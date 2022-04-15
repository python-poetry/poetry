from __future__ import annotations

from typing import cast

from cleo.helpers import argument
from cleo.helpers import option
from cleo.io.inputs.string_input import StringInput
from cleo.io.io import IO

from poetry.console.application import Application
from poetry.console.commands.command import Command
from poetry.console.commands.self.remove import SelfRemoveCommand


class PluginRemoveCommand(Command):

    name = "plugin remove"

    description = "Removes installed plugins"

    arguments = [
        argument("plugins", "The names of the plugins to install.", multiple=True),
    ]

    options = [
        option(
            "dry-run",
            None,
            "Output the operations but do not execute anything (implicitly enables"
            " --verbose).",
        )
    ]

    help = (
        "<warning>This command is deprecated. Use <c2>self remove</> command instead."
        "</warning>"
    )

    def handle(self) -> int:
        self.line_error(self.help)

        application = cast(Application, self.application)
        command: SelfRemoveCommand = cast(
            SelfRemoveCommand, application.find("self remove")
        )
        application._configure_installer(command, self.io)

        argv: list[str] = ["remove", *self.argument("plugins")]

        if self.option("--dry-run"):
            argv.append("--dry-run")

        exit_code: int = command.run(
            IO(
                StringInput(" ".join(argv)),
                self._io.output,
                self._io.error_output,
            )
        )
        return exit_code
