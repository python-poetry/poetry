from __future__ import annotations

import re

from typing import TYPE_CHECKING
from typing import ClassVar

from cleo.helpers import argument
from cleo.helpers import option
from packaging.utils import canonicalize_name

from poetry.console.commands.installer_command import InstallerCommand


if TYPE_CHECKING:
    from cleo.io.inputs.argument import Argument
    from cleo.io.inputs.option import Option

_VERSION_SPECIFIER_RE = re.compile(r"[><=!~]")


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
            # Detect version specifiers in package arguments — poetry update
            # only accepts bare package names, not requirement strings.
            packages_with_specifiers = [
                p for p in packages if _VERSION_SPECIFIER_RE.search(p)
            ]
            if packages_with_specifiers:
                self.line_error(
                    "<error>Version specifiers are not allowed in"
                    " <c1>poetry update</c1>.</error>"
                )
                for pkg in packages_with_specifiers:
                    self.line_error(f"  - {pkg}")
                self.line_error(
                    "Use <c1>poetry add</c1> to change version constraints."
                )
                return 1

            # Validate that all specified packages are declared dependencies
            all_dependencies = {dep.name for dep in self.poetry.package.all_requires}

            invalid_packages = [
                p for p in packages if canonicalize_name(p) not in all_dependencies
            ]

            if invalid_packages:
                self.line_error(
                    "<error>The following packages are not dependencies"
                    f" of this project: {', '.join(invalid_packages)}</error>"
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
