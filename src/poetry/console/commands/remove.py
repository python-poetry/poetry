from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

from cleo.helpers import argument
from cleo.helpers import option
from packaging.utils import canonicalize_name
from poetry.core.packages.dependency import Dependency
from poetry.core.packages.dependency_group import MAIN_GROUP
from tomlkit.toml_document import TOMLDocument

from poetry.console.commands.installer_command import InstallerCommand


if TYPE_CHECKING:
    from collections.abc import Mapping

    from cleo.io.inputs.argument import Argument
    from cleo.io.inputs.option import Option


class RemoveCommand(InstallerCommand):
    name = "remove"
    description = "Removes a package from the project dependencies."

    arguments: ClassVar[list[Argument]] = [
        argument("packages", "The packages to remove.", multiple=True)
    ]
    options: ClassVar[list[Option]] = [
        option("group", "G", "The group to remove the dependency from.", flag=False),
        option(
            "dev",
            "D",
            "Remove a package from the development dependencies."
            " (shortcut for '-G dev')",
        ),
        option(
            "dry-run",
            None,
            "Output the operations but do not execute anything "
            "(implicitly enables --verbose).",
        ),
        option("lock", None, "Do not perform operations (only update the lockfile)."),
    ]

    help = """The <info>remove</info> command removes a package from the current
list of installed packages

<info>poetry remove</info>"""

    loggers: ClassVar[list[str]] = [
        "poetry.repositories.pypi_repository",
        "poetry.inspection.info",
    ]

    def handle(self) -> int:
        packages = self.argument("packages")

        if self.option("dev"):
            group = "dev"
        else:
            group = self.option("group", self.default_group)

        content: dict[str, Any] = self.poetry.file.read()
        project_content = content.get("project", {})
        groups_content = content.get("dependency-groups", {})
        poetry_content = content.get("tool", {}).get("poetry", {})
        poetry_groups_content = poetry_content.get("group", {})

        if group is None:
            # remove from all groups
            removed = set()
            group_sections = []
            project_dependencies = project_content.get("dependencies", [])
            poetry_dependencies = poetry_content.get("dependencies", {})

            if project_dependencies or poetry_dependencies:
                group_sections.append(
                    (MAIN_GROUP, project_dependencies, poetry_dependencies)
                )
            group_sections.extend(
                (
                    group_name,
                    dependencies,
                    poetry_groups_content.get(group_name, {}).get("dependencies", {}),
                )
                for group_name, dependencies in groups_content.items()
            )
            group_sections.extend(
                (group_name, [], group_section.get("dependencies", {}))
                for group_name, group_section in poetry_groups_content.items()
                if group_name not in groups_content and group_name != MAIN_GROUP
            )

            for group_name, standard_section, poetry_section in group_sections:
                removed |= self._remove_packages(
                    packages=packages,
                    standard_section=standard_section,
                    poetry_section=poetry_section,
                    group_name=group_name,
                )
                if group_name != MAIN_GROUP:
                    if (
                        not poetry_section
                        and "dependencies" in poetry_groups_content.get(group_name, {})
                    ):
                        del poetry_content["group"][group_name]["dependencies"]
                        if not poetry_content["group"][group_name]:
                            del poetry_content["group"][group_name]
                    if not standard_section and group_name in groups_content:
                        del groups_content[group_name]
                    if (
                        group_name not in groups_content
                        and group_name not in poetry_groups_content
                    ):
                        self._remove_references_to_group(group_name, content)

        elif group == "dev" and "dev-dependencies" in poetry_content:
            # We need to account for the old `dev-dependencies` section
            removed = self._remove_packages(
                packages, [], poetry_content["dev-dependencies"], "dev"
            )

            if not poetry_content["dev-dependencies"]:
                del poetry_content["dev-dependencies"]
        else:
            removed = set()
            if group_content := poetry_groups_content.get(group):
                poetry_section = group_content.get("dependencies", {})
                removed.update(
                    self._remove_packages(
                        packages=packages,
                        standard_section=[],
                        poetry_section=poetry_section,
                        group_name=group,
                    )
                )
                if not poetry_section and "dependencies" in group_content:
                    del group_content["dependencies"]
                    if not group_content:
                        del poetry_content["group"][group]
            if group in groups_content:
                removed.update(
                    self._remove_packages(
                        packages=packages,
                        standard_section=groups_content[group],
                        poetry_section={},
                        group_name=group,
                    )
                )
                if not groups_content[group]:
                    del groups_content[group]
            if group not in groups_content and group not in poetry_groups_content:
                self._remove_references_to_group(group, content)

        if "group" in poetry_content and not poetry_content["group"]:
            del poetry_content["group"]
        if "dependency-groups" in content and not content["dependency-groups"]:
            del content["dependency-groups"]

        not_found = set(packages).difference(removed)
        if not_found:
            raise ValueError(
                "The following packages were not found: " + ", ".join(sorted(not_found))
            )

        # Refresh the locker
        self.poetry.locker.set_pyproject_data(content)
        self.installer.set_locker(self.poetry.locker)
        self.installer.set_package(self.poetry.package)
        self.installer.dry_run(self.option("dry-run", False))
        self.installer.verbose(self.io.is_verbose())
        self.installer.update(True)
        self.installer.execute_operations(not self.option("lock"))
        self.installer.whitelist(removed)

        status = self.installer.run()

        if not self.option("dry-run") and status == 0:
            assert isinstance(content, TOMLDocument)
            self.poetry.file.write(content)

        return status

    def _remove_packages(
        self,
        packages: list[str],
        standard_section: list[str | Mapping[str, Any]],
        poetry_section: dict[str, Any],
        group_name: str,
    ) -> set[str]:
        removed = set()
        group = self.poetry.package.dependency_group(group_name)

        for package in packages:
            normalized_name = canonicalize_name(package)
            for requirement in standard_section.copy():
                if not isinstance(requirement, str):
                    continue
                if Dependency.create_from_pep_508(requirement).name == normalized_name:
                    standard_section.remove(requirement)
                    removed.add(package)
            for existing_package in list(poetry_section):
                if canonicalize_name(existing_package) == normalized_name:
                    del poetry_section[existing_package]
                    removed.add(package)

        for package in removed:
            group.remove_dependency(package)

        return removed

    def _remove_references_to_group(
        self, group_name: str, content: dict[str, Any]
    ) -> None:
        """
        Removes references to the given group from other groups.
        """
        # 1. PEP 735: [dependency-groups]
        if "dependency-groups" in content:
            groups_to_remove = []
            for group_key, group_content in content["dependency-groups"].items():
                if not isinstance(group_content, list):
                    continue

                to_remove = []
                for item in group_content:
                    if (
                        isinstance(item, dict)
                        and item.get("include-group") == group_name
                    ):
                        to_remove.append(item)

                for item in to_remove:
                    group_content.remove(item)

                # Clean up now-empty lists (normalize with legacy behavior)
                # Only remove groups that became empty due to include-group cleanup,
                # not the target group itself (which is handled by the caller)
                if not group_content and group_key != group_name:
                    groups_to_remove.append(group_key)

            for group_key in groups_to_remove:
                del content["dependency-groups"][group_key]

        # 2. Legacy: [tool.poetry.group.<name>] include-groups = [...]
        poetry_content = content.get("tool", {}).get("poetry", {})
        if "group" in poetry_content:
            groups_to_remove = []
            for group_key, group_content in poetry_content["group"].items():
                if "include-groups" not in group_content:
                    continue

                if group_name in group_content["include-groups"]:
                    group_content["include-groups"].remove(group_name)

                if not group_content["include-groups"]:
                    del group_content["include-groups"]

                    if not group_content:
                        groups_to_remove.append(group_key)

            for group_key in groups_to_remove:
                del poetry_content["group"][group_key]
