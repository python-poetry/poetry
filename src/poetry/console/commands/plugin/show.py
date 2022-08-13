from __future__ import annotations

from cleo.io.inputs.string_input import StringInput
from cleo.io.io import IO

from poetry.console.commands.command import Command


class PluginShowCommand(Command):
    name = "plugin show"

    description = "Shows information about the currently installed plugins."
    help = (
        "<warning>This command is deprecated. Use <c2>self show plugins</> "
        "command instead.</warning>"
    )
    hidden = True

    def handle(self) -> int:
        self.line_error(self.help)

        application = self.get_application()
        command = application.find("self show plugins")

        return command.run(
            IO(
                StringInput(""),
                self.io.output,
                self.io.error_output,
            )
        )
