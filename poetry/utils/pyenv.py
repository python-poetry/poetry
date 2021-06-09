import os
import shutil
import subprocess

from pathlib import Path
from typing import Optional
from typing import Set

from poetry.utils._compat import decode
from poetry.utils._compat import list_to_shell_command


class PyenvNotFound(Exception):
    pass


class Pyenv:
    def __init__(self) -> None:
        self._command = None
        self._versions = None
        self._version = None

    def __bool__(self) -> bool:
        return self._command is not None and self._version is not None

    def load(self) -> None:
        if self._command is not None:
            return

        self._command = self.__locate_command()
        self._version = self.__read_pyenv_version()

    def __locate_command(self) -> Optional[Path]:
        candidates = []
        which_pyenv = shutil.which("pyenv")
        if which_pyenv is not None:
            candidates.append(Path(which_pyenv))

        candidates.extend(
            [
                Path(os.environ.get("PYENV_ROOT", "")) / "bin" / "pyenv",
                Path.home() / ".pyenv" / "bin" / "pyenv",
            ]
        )

        for candidate in candidates:
            if candidate.exists():
                return candidate

        raise PyenvNotFound

    def __read_pyenv_version(self) -> Optional[str]:
        try:
            version_no = decode(
                subprocess.check_output(
                    list_to_shell_command([str(self._command), "--version"]),
                    shell=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
            )
            if version_no.startswith("pyenv"):
                return version_no
        except Exception:
            pass
        return None

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
