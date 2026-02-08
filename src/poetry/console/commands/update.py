from __future__ import annotations

import re

from typing import TYPE_CHECKING
from typing import ClassVar

from cleo.helpers import argument
from cleo.helpers import option
from packaging.requirements import InvalidRequirement
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from poetry.console.commands.installer_command import InstallerCommand


if TYPE_CHECKING:
    from cleo.io.inputs.argument import Argument
    from cleo.io.inputs.option import Option

# PEP 508 package name pattern
_PACKAGE_NAME_RE = re.compile(r"^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)")


def _extract_package_name(package: str) -> str:
    """Extract the package name from a requirement string.

    Handles PEP 508 requirement strings (with extras, version specifiers,
    environment markers, and URLs) as well as non-standard operators like
    Poetry's ``^`` and ``~``.
    """
    package = package.strip()
    try:
        return Requirement(package).name
    except InvalidRequirement:
        # Fall back to regex for non-PEP-508 input (e.g. Poetry's ^ or ~)
        match = _PACKAGE_NAME_RE.match(package)
        if match:
            return match.group(1)
        return package


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
                package_name = _extract_package_name(package)
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
