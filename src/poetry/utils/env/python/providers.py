from __future__ import annotations

import shutil

from pathlib import Path
from typing import TYPE_CHECKING

import findpython


if TYPE_CHECKING:
    from collections.abc import Iterable

    from typing_extensions import Self


class ShutilWhichPythonProvider(findpython.BaseProvider):  # type: ignore[misc]
    @classmethod
    def create(cls) -> Self | None:
        return cls()

    def find_pythons(self) -> Iterable[findpython.PythonVersion]:
        if path := shutil.which("python"):
            return [findpython.PythonVersion(executable=Path(path))]
        return []
