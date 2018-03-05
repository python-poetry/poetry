import toml

from pathlib import Path

from poetry.toml import dumps
from poetry.toml import loads
from poetry.toml import TOMLFile


class TomlFile:

    def __init__(self, path):
        self._path = Path(path)

    @property
    def path(self):
        return self._path

    def read(self, raw=False) -> dict:
        if raw:
            return toml.loads(self._path.read_text())

        return loads(self._path.read_text())

    def write(self, data) -> None:
        if not isinstance(data, TOMLFile):
            data = toml.dumps(data)
        else:
            data = dumps(data)

        self._path.write_text(data)

    def exists(self) -> bool:
        return self._path.exists()
