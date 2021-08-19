from typing import Any
from typing import Dict
from typing import List

from cleo.helpers import argument
from cleo.helpers import option

from .installer_command import InstallerCommand


class RemoveCommand(InstallerCommand):

    name = "remove"
    description = "Removes a package from the project dependencies."

    arguments = [argument("packages", "The packages to remove.", multiple=True)]
    options = [
        option("group", "G", "The group to remove the dependency from.", flag=False),
        option("dev", "D", "Remove a package from the development dependencies."),
        option(
            "dry-run",
            None,
            "Output the operations but do not execute anything "
            "(implicitly enables --verbose).",
        ),
    ]

    help = """The <info>remove</info> command removes a package from the current
list of installed packages

<info>poetry remove</info>"""

    loggers = ["poetry.repositories.pypi_repository", "poetry.inspection.info"]

    def handle(self) -> int:
        packages = self.argument("packages")

        if self.option("dev"):
            self.line(
                "<warning>The --dev option is deprecated, "
                "use the `--group dev` notation instead.</warning>"
            )
            self.line("")
            group = "dev"
        else:
            group = self.option("group")

        content = self.poetry.file.read()
        poetry_content = content["tool"]["poetry"]

        if group is None:
            removed = []
            group_sections = []
            for group_name, group_section in poetry_content.get("group", {}).items():
                group_sections.append(
                    (group_name, group_section.get("dependencies", {}))
                )

            for group_name, section in [
                ("default", poetry_content["dependencies"])
            ] + group_sections:
                removed += self._remove_packages(packages, section, group_name)
                if group_name != "default":
                    if not section:
                        del poetry_content["group"][group_name]
                    else:
                        poetry_content["group"][group_name]["dependencies"] = section
        elif group == "dev" and "dev-dependencies" in poetry_content:
            # We need to account for the old `dev-dependencies` section
            removed = self._remove_packages(
                packages, poetry_content["dev-dependencies"], "dev"
            )

            if not poetry_content["dev-dependencies"]:
                del poetry_content["dev-dependencies"]
        else:
            removed = self._remove_packages(
                packages, poetry_content["group"][group].get("dependencies", {}), group
            )

            if not poetry_content["group"][group]:
                del poetry_content["group"][group]

        if "group" in poetry_content and not poetry_content["group"]:
            del poetry_content["group"]

        removed = set(removed)
        not_found = set(packages).difference(removed)
        if not_found:
            raise ValueError(
                "The following packages were not found: {}".format(
                    ", ".join(sorted(not_found))
                )
            )

        # Refresh the locker
        self.poetry.set_locker(
            self.poetry.locker.__class__(self.poetry.locker.lock.path, poetry_content)
        )
        self._installer.set_locker(self.poetry.locker)

        # Update packages
        self._installer.use_executor(
            self.poetry.config.get("experimental.new-installer", False)
        )

        self._installer.dry_run(self.option("dry-run"))
        self._installer.verbose(self._io.is_verbose())
        self._installer.update(True)
        self._installer.whitelist(removed)

        status = self._installer.run()

        if not self.option("dry-run") and status == 0:
            self.poetry.file.write(content)

        return status

    def _remove_packages(
        self, packages: List[str], section: Dict[str, Any], group_name: str
    ) -> List[str]:
        removed = []
        group = self.poetry.package.dependency_group(group_name)
        section_keys = list(section.keys())

        for package in packages:
            for existing_package in section_keys:
                if existing_package.lower() == package.lower():
                    del section[existing_package]
                    removed.append(package)
                    group.remove_dependency(package)

        return removed
