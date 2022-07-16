from __future__ import annotations

from typing import TYPE_CHECKING

from cleo.helpers import argument
from cleo.helpers import option
from cleo.io.inputs.string_input import StringInput
from cleo.io.io import IO

from poetry.console.commands.command import Command


if TYPE_CHECKING:
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

    hidden = True

    def handle(self) -> int:
        self.line_error(self.help)

        application = self.get_application()
        command: SelfRemoveCommand = application.find("self remove")
        application.configure_installer_for_command(command, self.io)

        argv: list[str] = ["remove", *self.argument("plugins")]

        if self.option("--dry-run"):
            argv.append("--dry-run")

        exit_code: int = command.run(
            IO(
                StringInput(" ".join(argv)),
                self.io.output,
                self.io.error_output,
            )
        )
        return exit_code
