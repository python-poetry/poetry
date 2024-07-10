from __future__ import annotations

import os
import sys

from typing import TYPE_CHECKING
from typing import cast

from poetry.console.commands.env_command import EnvCommand


if TYPE_CHECKING:
    from poetry.utils.env import VirtualEnv


class ShellCommand(EnvCommand):
    name = "shell"
    description = "Spawns a shell within the virtual environment."

    help = f"""The <info>shell</> command spawns a shell within the project's virtual environment.

By default, the current active shell is detected and used. Failing that,
the shell defined via the environment variable <comment>{'COMSPEC' if os.name == 'nt' else 'SHELL'}</> is used.

If a virtual environment does not exist, it will be created.
"""

    def handle(self) -> int:
        from poetry.utils.shell import Shell

        # Check if it's already activated or doesn't exist and won't be created
        if self._is_venv_activated():
            self.line(
                f"Virtual environment already activated: <info>{self.env.path}</>"
            )

            return 0

        self.line(f"Spawning shell within <info>{self.env.path}</>")

        # Be sure that we have the right type of environment.
        env = self.env
        assert env.is_venv()
        env = cast("VirtualEnv", env)

        # Setting this to avoid spawning unnecessary nested shells
        os.environ["POETRY_ACTIVE"] = "1"
        shell = Shell.get()
        shell.activate(env)
        os.environ.pop("POETRY_ACTIVE")

        return 0

    def _is_venv_activated(self) -> bool:
        return bool(os.environ.get("POETRY_ACTIVE")) or getattr(
            sys, "real_prefix", sys.prefix
        ) == str(self.env.path)
