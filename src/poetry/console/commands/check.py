from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

from cleo.helpers import option
from poetry.core.utils.helpers import module_name

from poetry.console.commands.command import Command


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.io.inputs.option import Option


class CheckCommand(Command):
    name = "check"
    description = (
        "Validates the content of the <comment>pyproject.toml</> file and its"
        " consistency with the poetry.lock file."
    )

    options: ClassVar[list[Option]] = [
        option(
            "lock",
            None,
            "Checks that <comment>poetry.lock</> exists for the current"
            " version of <comment>pyproject.toml</>.",
        ),
        option(
            "strict",
            None,
            "Fail if check reports warnings.",
        ),
    ]

    def _validate_classifiers(
        self, project_classifiers: set[str]
    ) -> tuple[list[str], list[str]]:
        """Identify unrecognized and deprecated trove classifiers.

        A fully-qualified classifier is a string delimited by `` :: `` separators. To
        make the error message more readable we need to have visual clues to
        materialize the start and end of a classifier string. That way the user can
        easily copy and paste it from the messages while reducing mistakes because of
        extra spaces.

        We use ``!r`` (``repr()``) for classifiers and list of classifiers for
        consistency. That way all strings will be rendered with the same kind of quotes
        (i.e. simple tick: ``'``).
        """
        from trove_classifiers import classifiers
        from trove_classifiers import deprecated_classifiers

        errors = []
        warnings = []

        unrecognized = sorted(
            project_classifiers - set(classifiers) - set(deprecated_classifiers)
        )
        # Allow "Private ::" classifiers as recommended on PyPI and the packaging guide
        # to allow users to avoid accidentally publishing private packages to PyPI.
        # https://pypi.org/classifiers/
        unrecognized = [u for u in unrecognized if not u.startswith("Private ::")]
        if unrecognized:
            errors.append(f"Unrecognized classifiers: {unrecognized!r}.")

        deprecated = sorted(
            project_classifiers.intersection(set(deprecated_classifiers))
        )
        if deprecated:
            for old_classifier in deprecated:
                new_classifiers = deprecated_classifiers[old_classifier]
                if new_classifiers:
                    message = (
                        f"Deprecated classifier {old_classifier!r}. "
                        f"Must be replaced by {new_classifiers!r}."
                    )
                else:
                    message = (
                        f"Deprecated classifier {old_classifier!r}. Must be removed."
                    )
                warnings.append(message)

        return errors, warnings

    def _validate_readme(self, readme: str | list[str], poetry_file: Path) -> list[str]:
        """Check existence of referenced readme files"""

        readmes = [readme] if isinstance(readme, str) else readme

        errors = []
        for name in readmes:
            if not (poetry_file.parent / name).exists():
                errors.append(f"Declared README file does not exist: {name}")
        return errors

    def _validate_dependencies_source(self, config: dict[str, Any]) -> list[str]:
        """Check dependencies's source are valid"""
        sources = {repository.name for repository in self.poetry.pool.all_repositories}

        dependency_declarations: list[
            dict[str, str | dict[str, str] | list[dict[str, str]]]
        ] = []
        # scan dependencies and group dependencies settings in pyproject.toml
        if "dependencies" in config:
            dependency_declarations.append(config["dependencies"])

        for group in config.get("group", {}).values():
            if "dependencies" in group:
                dependency_declarations.append(group["dependencies"])

        all_referenced_sources: set[str] = set()

        for dependency_declaration in dependency_declarations:
            for declaration in dependency_declaration.values():
                if isinstance(declaration, list):
                    for item in declaration:
                        if "source" in item:
                            all_referenced_sources.add(item["source"])
                elif isinstance(declaration, dict) and "source" in declaration:
                    all_referenced_sources.add(declaration["source"])

        return [
            f'Invalid source "{source}" referenced in dependencies.'
            for source in sorted(all_referenced_sources - sources)
        ]

    def _validate_project_in_src(
        self, toml_data: dict[str, Any], base_path: Path | None
    ) -> list[str]:
        """
        Checks the validity of projects located under src/ subdirectory.
        """
        result: list[str] = []

        print(base_path)

        project_name = toml_data.get("project", {}).get("name") or toml_data.get(
            "tool", {}
        ).get("poetry", {}).get("name")

        print(project_name)
        if project_name is None or base_path is None:
            return result

        project_name = module_name(project_name)

        print(project_name)

        project_dir = base_path / project_name
        src_project_dir = base_path / "src" / project_name

        project_dir_empty = (
            project_dir.exists()
            and project_dir.is_dir()
            and not any(project_dir.iterdir())
        )
        src_dir_not_empty = (
            src_project_dir.exists()
            and src_project_dir.is_dir()
            and any(src_project_dir.iterdir())
        )

        print(project_dir_empty)
        print(src_dir_not_empty)

        if project_dir_empty and src_dir_not_empty:
            result.append(
                f"Found empty directory '{project_name}' in project root while the actual package is in "
                f"'src/{project_name}'. This may cause issues with package installation. "
                "Consider removing the empty directory."
            )

        return result

    def handle(self) -> int:
        from poetry.core.pyproject.toml import PyProjectTOML

        from poetry.factory import Factory

        # Load poetry config and display errors, if any
        poetry_file = self.poetry.file.path
        toml_data = PyProjectTOML(poetry_file).data
        check_result = Factory.validate(toml_data, strict=True)

        project = toml_data.get("project", {})
        poetry_config = toml_data["tool"]["poetry"]

        # Validate trove classifiers
        project_classifiers = set(
            project.get("classifiers") or poetry_config.get("classifiers", [])
        )
        errors, warnings = self._validate_classifiers(project_classifiers)
        check_result["errors"].extend(errors)
        check_result["warnings"].extend(warnings)

        project_root = poetry_file.parent
        warnings = self._validate_project_in_src(toml_data, project_root)
        check_result["warnings"].extend(warnings)

        # Validate readme (files must exist)
        # TODO: consider [project.readme] as well
        if "readme" in poetry_config:
            errors = self._validate_readme(poetry_config["readme"], poetry_file)
            check_result["errors"].extend(errors)

        check_result["errors"] += self._validate_dependencies_source(poetry_config)

        # Verify that lock file is consistent
        if self.option("lock") and not self.poetry.locker.is_locked():
            check_result["errors"] += ["poetry.lock was not found."]
        if self.poetry.locker.is_locked() and not self.poetry.locker.is_fresh():
            check_result["errors"] += [
                "pyproject.toml changed significantly since poetry.lock was last generated. "
                "Run `poetry lock` to fix the lock file."
            ]

        return_code = 0

        if check_result["errors"] or (
            check_result["warnings"] and self.option("strict")
        ):
            return_code = 1

        if not check_result["errors"] and not check_result["warnings"]:
            self.info("All set!")

        for error in check_result["errors"]:
            self.line_error(f"<error>Error: {error}</error>")

        for error in check_result["warnings"]:
            self.line_error(f"<warning>Warning: {error}</warning>")

        return return_code
