from __future__ import annotations

from typing import TYPE_CHECKING

import tomlrt


if TYPE_CHECKING:
    from pathlib import Path

    from tomlrt import Document


class TOMLFile:
    """
    Represents a TOML file backed by tomlrt for format-preserving I/O.
    """

    def __init__(self, path: Path) -> None:
        self.__path = path

    @property
    def path(self) -> Path:
        return self.__path

    def exists(self) -> bool:
        return self.__path.exists()

    def read(self) -> Document:
        from poetry.toml import TOMLError

        try:
            with open(self.__path, "rb") as f:
                return tomlrt.load(f)
        except tomlrt.TOMLError as e:
            raise TOMLError(f"Invalid TOML file {self.__path.as_posix()}: {e}")

    def write(self, data: Document) -> None:
        with open(self.__path, "wb") as f:
            tomlrt.dump(data, f)

    def __str__(self) -> str:
        return self.__path.as_posix()
