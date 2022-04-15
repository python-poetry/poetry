from __future__ import annotations

from typing import cast

from cleo.helpers import argument
from cleo.helpers import option
from cleo.io.inputs.string_input import StringInput
from cleo.io.io import IO

from poetry.console.application import Application
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

    def handle(self) -> int:
        self.line_error(self.deprecation)

        application = cast(Application, self.application)
        command: SelfAddCommand = cast(SelfAddCommand, application.find("self add"))
        application._configure_installer(command, self.io)

        argv: list[str] = ["add", *self.argument("plugins")]

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
