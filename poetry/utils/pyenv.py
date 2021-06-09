import os
import shutil
import subprocess

from pathlib import Path
from typing import Optional
from typing import Set

from poetry.utils._compat import decode
from poetry.utils._compat import list_to_shell_command


class PyEnvNotFound(Exception):
    pass


class PyEnv:
    def __init__(self) -> None:
        self._command = None
        self._versions = None
        self._prefix = None

    def __bool__(self) -> bool:
        return self._command is not None

    def load(self) -> None:
        if self._command is not None:
            return

        self._command = self.__locate_command()

    def __locate_command(self) -> Optional[Path]:
        which_pyenv = shutil.which("pyenv")
        if which_pyenv is not None:
            return Path(which_pyenv)

        pyenv_root = Path(os.environ.get("PYENV_ROOT"))
        if pyenv_root is None:
            pyenv_root = Path.home() / ".pyenv"

        if pyenv_root.exists():
            which_pyenv = pyenv_root / "bin" / "pyenv"
            if which_pyenv.exists():
                return which_pyenv
        raise PyEnvNotFound

    def versions(self) -> Set[str]:
        """List all python versions installed by pyenv."""
        if self._versions is not None:
            return self._versions

        output = decode(
            subprocess.check_output(
                list_to_shell_command(
                    [str(self._command), "versions", "--bare", "--skip-aliases"]
                ),
                shell=True,
            )
        )
        self._versions = set(output.split("\n"))
        self._versions.discard("")
        return self._versions

    def executable(self, version) -> Path:
        prefix = decode(
            subprocess.check_output(
                list_to_shell_command([str(self._command), "prefix", version]),
                shell=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        )
        return Path(prefix) / "bin" / "python"
