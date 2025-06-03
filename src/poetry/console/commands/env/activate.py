from __future__ import annotations

import shlex

from typing import TYPE_CHECKING

import shellingham

from poetry.console.commands.env_command import EnvCommand
from poetry.utils._compat import WINDOWS


if TYPE_CHECKING:
    from poetry.utils.env import Env


class ShellNotSupportedError(Exception):
    """Raised when a shell doesn't have an activator in virtual environment"""


class EnvActivateCommand(EnvCommand):
    name = "env activate"
    description = "Print the command to activate a virtual environment."

    def handle(self) -> int:
        from poetry.utils.env import EnvManager

        env = EnvManager(self.poetry).get()

        try:
            shell, *_ = shellingham.detect_shell()
        except shellingham.ShellDetectionFailure:
            shell = ""

        if command := self._get_activate_command(env, shell):
            self.line(command)
            return 0

        raise ShellNotSupportedError(
            f"Discovered shell '{shell}' doesn't have an activator in virtual environment"
        )

    def _get_activate_command(self, env: Env, shell: str) -> str:
        shell_configs = {
            "fish": ("source", "activate.fish"),
            "nu": ("overlay use", "activate.nu"),
            "csh": ("source", "activate.csh"),
            "tcsh": ("source", "activate.csh"),
            "powershell": (".", "activate.ps1"),
            "pwsh": (".", "activate.ps1"),
            "cmd": (".", "activate.bat"),
        }

        command, filename = shell_configs.get(shell, ("source", "activate"))

        activation_script = env.bin_dir / filename

        if not activation_script.exists():
            if shell == "cmd" and not WINDOWS:
                fallback_script = env.bin_dir / "activate"
                if fallback_script.exists():
                    return f"source {self._quote(str(fallback_script), 'bash')}"
            return ""

        if shell in ["powershell", "pwsh"]:
            return f'& "{activation_script}"'
        elif shell == "cmd":
            return f'"{activation_script}"'
        else:
            return f"{command} {self._quote(str(activation_script), shell)}"

    @staticmethod
    def _quote(command: str, shell: str) -> str:
        if WINDOWS and shell not in ["powershell", "pwsh", "cmd"]:
            return shlex.quote(command)
        elif shell in ["powershell", "pwsh", "cmd"]:
            return command
        else:
            return shlex.quote(command)
