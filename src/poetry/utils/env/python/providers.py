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
        install_dir = base or Config.create().python_installation_dir
        if WINDOWS and not sysconfig.get_platform().startswith("mingw"):
            # On Windows Python executables are top level.
            # (Only in virtualenvs, they are in the Scripts directory.)
            # A python-build-standalone PyPy has no Scripts directory!
            if base:
                return [base] if base.is_dir() else []
            return [p for p in Path.glob(install_dir, "*") if p.is_dir()]
        return list(Path.glob(install_dir, "**/bin"))

    @classmethod
    def installation_bin_paths(
        cls, version: Version, implementation: str
    ) -> list[Path]:
        return cls._make_bin_paths(cls.installation_dir(version, implementation))

    @classmethod
    def create(cls) -> Self | None:
        return cls(cls._make_bin_paths())
