import subprocess

from pathlib import Path
from typing import Optional
from typing import Set

from poetry.core.semver.version import VersionTypes
from poetry.utils._compat import decode
from poetry.utils._compat import list_to_shell_command


class Pyenv:
    """
    Pyenv
    """

    def __init__(self) -> None:
        self._command = None
        self._versions = None

    @classmethod
    def load(cls) -> "Pyenv":
        inst = cls()
        inst._command = inst._locate_command()
        if inst._command is None:  # pyenv not found
            return inst
        return inst

    def __bool__(self) -> bool:
        return self._command is not None

    def _locate_command(self) -> Optional[Path]:
        # FIXME(ggicci): locate the pyenv command
        return Path("/home/mingjietang/.pyenv/bin/pyenv")

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

    def lookup(self, python_constraint: VersionTypes) -> Path:
        # TODO(ggicci): try order
        # python_constraint.allows()
        return Path("/")

    def python_path(self, version) -> Path:
        prefix = decode(
            subprocess.check_output(
                list_to_shell_command([str(self._command), "prefix", version]),
                shell=True,
            )
        )
        return Path(prefix) / "bin" / "python"
