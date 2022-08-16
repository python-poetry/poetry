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

    def handle(self) -> int:
        from poetry.utils.shell import Shell

        # Check if it's already activated or doesn't exist and won't be created
        venv_activated = strtobool(environ.get("POETRY_ACTIVE", "0")) or getattr(
            sys, "real_prefix", sys.prefix
        ) == str(self.env.path)
        if venv_activated:
            self.line(
                f"Virtual environment already activated: <info>{self.env.path}</>"
            )

            return 0

        self.line(f"Spawning shell within <info>{self.env.path}</>")

        # Setting this to avoid spawning unnecessary nested shells
        environ["POETRY_ACTIVE"] = "1"
        shell = Shell.get()
        shell.activate(self.env)  # type: ignore[arg-type]
        environ.pop("POETRY_ACTIVE")

        return 0
