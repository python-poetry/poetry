from __future__ import annotations

from cleo.helpers import argument
from cleo.helpers import option
from cleo.io.inputs.string_input import StringInput
from cleo.io.io import IO

from poetry.console.commands.init import InitCommand
from poetry.console.commands.self.add import SelfAddCommand


class PluginAddCommand(InitCommand):
    name = "plugin add"

    description = "Adds new plugins."

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
    deprecation = (
        "<warning>This command is deprecated. Use <c2>self add</> command instead."
        "</warning>"
    )
    help = f"""
The <c1>plugin add</c1> command installs Poetry plugins globally.

It works similarly to the <c1>add</c1> command:

{SelfAddCommand.examples}

{deprecation}
"""
    hidden = True

    def handle(self) -> int:
        self.line_error(self.deprecation)

        application = self.get_application()
        command = application.find("self add")
        assert isinstance(command, SelfAddCommand)
        application.configure_installer_for_command(command, self.io)

        argv: list[str] = ["add", *self.argument("plugins")]

        if self.option("--dry-run"):
            argv.append("--dry-run")

        return command.run(
            IO(
                StringInput(" ".join(argv)),
                self.io.output,
                self.io.error_output,
            )
        )
