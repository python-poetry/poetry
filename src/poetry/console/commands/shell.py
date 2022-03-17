from __future__ import annotations

import sys

from distutils.util import strtobool
from os import environ

from poetry.console.commands.env_command import EnvCommand


class ShellCommand(EnvCommand):

    name = "shell"
    description = "Spawns a shell within the virtual environment."

    help = """The <info>shell</> command spawns a shell, according to the
<comment>$SHELL</> environment variable, within the virtual environment.
If one doesn't exist yet, it will be created.
"""

    def handle(self) -> None:
        from poetry.utils.shell import Shell

        # Check if it's already activated or doesn't exist and won't be created
        poetry_active = strtobool(environ.get("POETRY_ACTIVE", "0"))
        venv_activated = getattr(sys, "real_prefix", sys.prefix) == str(self.env.path)
        if poetry_active:
            if venv_activated:
                self.line(
                    f"Virtual environment already activated: <info>{self.env.path}</>"
                )
            else:
                self.line(
                    "Poetry shell is active but venv is deactivated. "
                    "Exit shell and re-launch."
                )
            return

        self.line(f"Spawning shell within <info>{self.env.path}</>")

        # Setting this to avoid spawning unnecessary nested shells
        environ["POETRY_ACTIVE"] = "1"
        shell = Shell.get()
        shell.activate(self.env)  # type: ignore[arg-type]
        environ.pop("POETRY_ACTIVE")
