import os
import signal
import sys

from pathlib import Path
from typing import Any

import pexpect

from cleo.terminal import Terminal
from shellingham import ShellDetectionFailure
from shellingham import detect_shell

from ._compat import WINDOWS
from .env import VirtualEnv


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
    def get(cls) -> "Shell":
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

    def activate(self, env: VirtualEnv) -> None:
        if WINDOWS:
            return env.execute(self.path)

        import shlex

        terminal = Terminal()
        with env.temp_environ():
            c = pexpect.spawn(
                self._path, ["-i"], dimensions=(terminal.height, terminal.width)
            )

        if self._name == "zsh":
            c.setecho(False)

        activate_script = self._get_activate_script()
        bin_dir = "Scripts" if WINDOWS else "bin"
        activate_path = env.path / bin_dir / activate_script
        c.sendline(
            "{} {}".format(self._get_source_command(), shlex.quote(str(activate_path)))
        )

        def resize(sig: Any, data: Any) -> None:
            terminal = Terminal()
            c.setwinsize(terminal.height, terminal.width)

        signal.signal(signal.SIGWINCH, resize)

        # Interact with the new shell.
        c.interact(escape_character=None)
        c.close()

        sys.exit(c.exitstatus)

    def _get_activate_script(self) -> str:
        if "fish" == self._name:
            suffix = ".fish"
        elif "csh" == self._name:
            suffix = ".csh"
        elif "tcsh" == self._name:
            suffix = ".csh"
        else:
            suffix = ""

        return "activate" + suffix

    def _get_source_command(self) -> str:
        if "fish" == self._name:
            return "source"
        elif "csh" == self._name:
            return "source"
        elif "tcsh" == self._name:
            return "source"

        return "."

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}("{self._name}", "{self._path}")'
