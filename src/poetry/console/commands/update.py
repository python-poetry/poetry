from __future__ import annotations

from typing import TYPE_CHECKING
from typing import ClassVar

from cleo.helpers import argument
from cleo.helpers import option
from packaging.utils import canonicalize_name

from poetry.console.commands.installer_command import InstallerCommand


if TYPE_CHECKING:
    from cleo.io.inputs.argument import Argument
    from cleo.io.inputs.option import Option


class UpdateCommand(InstallerCommand):
    name = "update"
    description = (
        "Update the dependencies as according to the <comment>pyproject.toml</> file."
    )

    arguments: ClassVar[list[Argument]] = [
        argument("packages", "The packages to update", optional=True, multiple=True)
    ]
    options: ClassVar[list[Option]] = [
        *InstallerCommand._group_dependency_options(),
        option(
            "sync",
            None,
            "Synchronize the environment with the locked packages and the specified"
            " groups.",
        ),
        option(
            "dry-run",
            None,
            "Output the operations but do not execute anything "
            "(implicitly enables --verbose).",
        ),
        option("lock", None, "Do not perform operations (only update the lockfile)."),
    ]

    loggers: ClassVar[list[str]] = ["poetry.repositories.pypi_repository"]

    def handle(self) -> int:
        packages = self.argument("packages")
        if packages:
            # Validate that all specified packages are declared dependencies
            all_dependencies = {
                canonicalize_name(dep.name) for dep in self.poetry.package.all_requires
            }

            invalid_packages = []
            for package in packages:
                # Check if package name contains version constraint
                # (e.g., "package==1.0.0" or "package>=1.0")
                package_name = package.split(">")[0].split("<")[0].split("=")[0].split("!")[0].strip()
                canonical_name = canonicalize_name(package_name)

                if canonical_name not in all_dependencies:
                    invalid_packages.append(package)

            if invalid_packages:
                self.line_error(
                    f"<error>The following packages are not dependencies of this project: "
                    f"{', '.join(invalid_packages)}</error>"
                )
                return 1

            self.installer.whitelist(dict.fromkeys(packages, "*"))

        self.installer.only_groups(self.activated_groups)
        self.installer.dry_run(self.option("dry-run"))
        self.installer.requires_synchronization(self.option("sync"))
        self.installer.execute_operations(not self.option("lock"))

        # Force update
        self.installer.update(True)

        return self.installer.run()
