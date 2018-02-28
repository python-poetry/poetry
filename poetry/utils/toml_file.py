from pathlib import Path

from toml import dumps
from toml import loads


class TomlFile:

    def __init__(self, path):
        self._path = Path(path)

    @property
    def path(self):
        return self._path

    def read(self) -> dict:
        return loads(self._path.read_text())

    def write(self, data) -> None:
        self._path.write_text(dumps(data))

    def exists(self) -> bool:
        return self._path.exists()
