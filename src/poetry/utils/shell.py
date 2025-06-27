from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pexpect

from shellingham import ShellDetectionFailure
from shellingham import detect_shell

from poetry.utils._compat import WINDOWS


if TYPE_CHECKING:
    from poetry.utils.env import VirtualEnv


class Shell:
    """
    Represents the current shell.
    """

    _shell = None

    def __init__(self, name: str, path: str) -> None:
        self._name = name
        self._path = path

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> str:
        return self._path

    @classmethod
    def get(cls) -> Shell:
        """
        Retrieve the current shell.
        """
        if cls._shell is not None:
            return cls._shell

        try:
            name, path = detect_shell(os.getpid())
        except (RuntimeError, ShellDetectionFailure):
            shell = None

            if os.name == "posix":
                shell = os.environ.get("SHELL")
            elif os.name == "nt":
                shell = os.environ.get("COMSPEC")

            if not shell:
                raise RuntimeError("Unable to detect the current shell.")

            name, path = Path(shell).stem, shell

        cls._shell = cls(name, path)

        return cls._shell

    def activate(self, env: VirtualEnv) -> int | None:
        activate_script = self._get_activate_script()
        if WINDOWS:
            bin_path = env.path / "Scripts"
            # Python innstalled via msys2 on Windows might produce a POSIX-like venv
            # See https://github.com/python-poetry/poetry/issues/8638
            bin_dir = "Scripts" if bin_path.exists() else "bin"
        else:
            bin_dir = "bin"
        activate_path = env.path / bin_dir / activate_script

        # mypy requires using sys.platform instead of WINDOWS constant
        # in if statements to properly type check on Windows
        if sys.platform == "win32":
            args = None
            if self._name in ("powershell", "pwsh"):
                args = ["-NoExit", "-File", str(activate_path)]
            elif self._name == "cmd":
                # /K will execute the bat file and
                # keep the cmd process from terminating
                args = ["/K", str(activate_path)]

            if args:
                completed_proc = subprocess.run([self.path, *args])
                return completed_proc.returncode
            else:
                # If no args are set, execute the shell within the venv
                # This activates it, but there could be some features missing:
                # deactivate command might not work
                # shell prompt will not be modified.
                return env.execute(self._path)

        import shlex

        terminal = shutil.get_terminal_size()
        cmd = f"{self._get_source_command()} {shlex.quote(str(activate_path))}"

        with env.temp_environ():
            if self._name == "nu":
                args = ["-e", cmd]
            elif self._name == "fish":
                args = ["-i", "--init-command", cmd]
            else:
                args = ["-i"]

            c = pexpect.spawn(
                self._path, args, dimensions=(terminal.lines, terminal.columns)
            )

        if self._name in ["zsh"]:
            c.setecho(False)

        if self._name == "zsh":
            # Under ZSH the source command should be invoked in zsh's bash emulator
            quoted_activate_path = shlex.quote(str(activate_path))
            c.sendline(f"emulate bash -c {shlex.quote(f'. {quoted_activate_path}')}")
        elif self._name == "xonsh":
            c.sendline(f"vox activate {shlex.quote(str(env.path))}")
        elif self._name in ["nu", "fish"]:
            # If this is nu or fish, we don't want to send the activation command to the
            # command line since we already ran it via the shell's invocation.
            pass
        else:
            c.sendline(cmd)

        def resize(sig: Any, data: Any) -> None:
            terminal = shutil.get_terminal_size()
            c.setwinsize(terminal.lines, terminal.columns)

        signal.signal(signal.SIGWINCH, resize)

        # Interact with the new shell.
        c.interact(escape_character=None)
        c.close()

        sys.exit(c.exitstatus)

    def _get_activate_script(self) -> str:
        if self._name == "fish":
            suffix = ".fish"
        elif self._name in ("csh", "tcsh"):
            suffix = ".csh"
        elif self._name in ("powershell", "pwsh"):
            suffix = ".ps1"
        elif self._name == "cmd":
            suffix = ".bat"
        elif self._name == "nu":
            suffix = ".nu"
        else:
            suffix = ""

        return "activate" + suffix

    def _get_source_command(self) -> str:
        if self._name in ("fish", "csh", "tcsh"):
            return "source"
        elif self._name == "nu":
            return "overlay use"
        return "."

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}("{self._name}", "{self._path}")'
