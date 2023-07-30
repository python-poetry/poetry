from __future__ import annotations

from typing import TYPE_CHECKING

from cleo.helpers import option

from poetry.console.commands.command import Command


if TYPE_CHECKING:
    from pathlib import Path


class CheckCommand(Command):
    name = "check"
    description = (
        "Validates the content of the <comment>pyproject.toml</> file and its"
        " consistency with the poetry.lock file."
    )

    options = [
        option(
            "lock",
            None,
            "Checks that <comment>poetry.lock</> exists for the current"
            " version of <comment>pyproject.toml</>.",
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

    def handle(self) -> int:
        from poetry.factory import Factory
        from poetry.pyproject.toml import PyProjectTOML

        # Load poetry config and display errors, if any
        poetry_file = self.poetry.file.path
        config = PyProjectTOML(poetry_file).poetry_config
        check_result = Factory.validate(config, strict=True)

        # Validate trove classifiers
        project_classifiers = set(config.get("classifiers", []))
        errors, warnings = self._validate_classifiers(project_classifiers)
        check_result["errors"].extend(errors)
        check_result["warnings"].extend(warnings)

        # Validate readme (files must exist)
        if "readme" in config:
            errors = self._validate_readme(config["readme"], poetry_file)
            check_result["errors"].extend(errors)

        # Verify that lock file is consistent
        if self.option("lock") and not self.poetry.locker.is_locked():
            check_result["errors"] += ["poetry.lock was not found."]
        if self.poetry.locker.is_locked() and not self.poetry.locker.is_fresh():
            check_result["errors"] += [
                "poetry.lock is not consistent with pyproject.toml. Run `poetry"
                " lock [--no-update]` to fix it."
            ]

        if not check_result["errors"] and not check_result["warnings"]:
            self.info("All set!")

            return 0

        for error in check_result["errors"]:
            self.line_error(f"<error>Error: {error}</error>")

        for error in check_result["warnings"]:
            self.line_error(f"<warning>Warning: {error}</warning>")

        return 1
