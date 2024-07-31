from __future__ import annotations

from typing import TYPE_CHECKING
from typing import ClassVar

from cleo.helpers import option

from poetry.console.commands.installer_command import InstallerCommand


if TYPE_CHECKING:
    from cleo.io.inputs.option import Option


class LockCommand(InstallerCommand):
    name = "lock"
    description = "Locks the project dependencies."

    options: ClassVar[list[Option]] = [
        option(
            "regenerate",
            None,
            "Ignore existing lock file"
            " and overwrite it with a new lock file created from scratch.",
        ),
        option(
            "check",
            None,
            "Check that the <comment>poetry.lock</> file corresponds to the current"
            " version of <comment>pyproject.toml</>. (<warning>Deprecated</>) Use"
            " <comment>poetry check --lock</> instead.",
        ),
    ]

    help = """
The <info>lock</info> command reads the <comment>pyproject.toml</> file from the
current directory, processes it, and locks the dependencies in the\
 <comment>poetry.lock</>
file.
By default, packages that have already been added to the lock file before
will not be updated.

<info>poetry lock</info>
"""

    loggers: ClassVar[list[str]] = ["poetry.repositories.pypi_repository"]

    def handle(self) -> int:
        if self.option("check"):
            self.line_error(
                "<warning>poetry lock --check is deprecated, use `poetry"
                " check --lock` instead.</warning>"
            )
            if self.poetry.locker.is_locked() and self.poetry.locker.is_fresh():
                self.line("poetry.lock is consistent with pyproject.toml.")
                return 0
            self.line_error(
                "<error>"
                "Error: pyproject.toml changed significantly since poetry.lock was last generated. "
                "Run `poetry lock [--no-update]` to fix the lock file."
                "</error>"
            )
            return 1

        self.installer.lock(update=self.option("regenerate"))

        return self.installer.run()
