from __future__ import annotations

import sys

from pathlib import Path
from typing import Any

from poetry.utils.env.system_env import SystemEnv


class NullEnv(SystemEnv):
    def __init__(
        self, path: Path | None = None, base: Path | None = None, execute: bool = False
    ) -> None:
        if path is None:
            path = Path(sys.prefix)

        super().__init__(path, base=base)

        self._execute = execute
        self.executed: list[list[str]] = []

    @property
    def paths(self) -> dict[str, str]:
        if self._paths is None:
            self._paths = self.get_paths()
            self._paths["platlib"] = str(self._path / "platlib")
            self._paths["purelib"] = str(self._path / "purelib")
            self._paths["scripts"] = str(self._path / "scripts")
            self._paths["data"] = str(self._path / "data")

        return self._paths

    def _run(self, cmd: list[str], **kwargs: Any) -> str:
        self.executed.append(cmd)

        if self._execute:
            return super()._run(cmd, **kwargs)
        return ""

    def execute(self, bin: str, *args: str, **kwargs: Any) -> int:
        self.executed.append([bin, *list(args)])

        if self._execute:
            return super().execute(bin, *args, **kwargs)
        return 0

    def _bin(self, bin: str) -> str:
        return bin
