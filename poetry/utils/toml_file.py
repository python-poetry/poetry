# -*- coding: utf-8 -*-
import toml

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
        with self._path.open() as f:
            if raw:
                return toml.loads(f.read())

            return loads(f.read())

    def write(self, data):  # type: (...) -> None
        if not isinstance(data, TOMLFile):
            data = toml.dumps(data)
        else:
            data = dumps(data)

        with self._path.open('w') as f:
            f.write(data)

    def __getattr__(self, item):
        return getattr(self._path, item)
