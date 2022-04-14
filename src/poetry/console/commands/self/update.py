from __future__ import annotations

from typing import cast

from cleo.helpers import argument
from cleo.helpers import option
from cleo.io.inputs.string_input import StringInput
from cleo.io.io import IO

from poetry.console.application import Application
from poetry.console.commands.add import AddCommand
from poetry.console.commands.self.self_command import SelfCommand


class SelfUpdateCommand(SelfCommand):
    name = "self update"
    description = "Updates Poetry to the latest version."

    arguments = [
        argument(
            "version", "The version to update to.", optional=True, default="latest"
        )
    ]
    options = [
        option("preview", None, "Allow the installation of pre-release versions."),
        option(
            "dry-run",
            None,
            "Output the operations but do not execute anything "
            "(implicitly enables --verbose).",
        ),
    ]
    help = """\
The <c1>self update</c1> command updates Poetry version in its current runtime \
environment.
"""

    def _system_project_handle(self) -> int:
        self.write("<info>Updating Poetry version ...</info>\n\n")
        application = cast(Application, self.application)
        add_command: AddCommand = cast(AddCommand, application.find("add"))
        add_command.set_env(self.env)
        application._configure_installer(add_command, self._io)

        argv = ["add", f"poetry@{self.argument('version')}"]

        if self.option("dry-run"):
            argv.append("--dry-run")

        if self.option("preview"):
            argv.append("--allow-prereleases")

        return add_command.run(
            IO(
                StringInput(" ".join(argv)),
                self._io.output,
                self._io.error_output,
            )
        )
