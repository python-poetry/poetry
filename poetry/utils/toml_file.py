# -*- coding: utf-8 -*-
import pytoml as toml

from poetry.toml import dumps
from poetry.toml import loads
from poetry.toml import TOMLFile

from ._compat import Path


class TomlFile:
    def __init__(self, path):
        self._path = Path(path)

    @property
    def path(self):
        return self._path

    def read(self, raw=False):  # type: (bool) -> dict
        with self._path.open(encoding="utf-8") as f:
            if raw:
                return toml.loads(f.read())

            return loads(f.read())

    def dumps(self, data, sort=False):  # type: (...) -> str
        if not isinstance(data, TOMLFile):
            data = toml.dumps(data, sort_keys=sort)
        else:
            data = dumps(data)

        return data

    def write(self, data, sort=False):  # type: (...) -> None
        data = self.dumps(data, sort=sort)

        with self._path.open("w", encoding="utf-8") as f:
            f.write(data)

    def __getattr__(self, item):
        return getattr(self._path, item)
