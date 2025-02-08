from __future__ import annotations

import dataclasses
import shutil
import sysconfig

from pathlib import Path
from typing import TYPE_CHECKING

import findpython

from findpython.providers.path import PathProvider

from poetry.config.config import Config
from poetry.utils._compat import WINDOWS


if TYPE_CHECKING:
    from collections.abc import Iterable

    from poetry.core.constraints.version import Version
    from typing_extensions import Self


class ShutilWhichPythonProvider(findpython.BaseProvider):  # type: ignore[misc]
    @classmethod
    def create(cls) -> Self | None:
        return cls()

    def find_pythons(self) -> Iterable[findpython.PythonVersion]:
        if path := shutil.which("python"):
            return [findpython.PythonVersion(executable=Path(path))]
        return []


@dataclasses.dataclass
class PoetryPythonPathProvider(PathProvider):  # type: ignore[misc]
    @classmethod
    def installation_dir(cls, version: Version, implementation: str) -> Path:
        return Config.create().python_installation_dir / f"{implementation}@{version}"

    @classmethod
    def _make_bin_paths(cls, base: Path | None = None) -> list[Path]:
        bin_dir_name = (
            "bin"
            if not WINDOWS or sysconfig.get_platform().startswith("mingw")
            else "Scripts"
        )
        return [
            Path(p.parent if p.name == "Scripts" else p)
            for p in Path.glob(
                base or Config.create().python_installation_dir,
                f"**/{bin_dir_name}",
            )
        ]

    @classmethod
    def installation_bin_paths(
        cls, version: Version, implementation: str
    ) -> list[Path]:
        return cls._make_bin_paths(cls.installation_dir(version, implementation))

    @classmethod
    def create(cls) -> Self | None:
        return cls(cls._make_bin_paths())
