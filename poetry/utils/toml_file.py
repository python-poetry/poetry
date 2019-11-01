# -*- coding: utf-8 -*-
from typing import Union

from tomlkit.toml_file import TOMLFile as BaseTOMLFile

from ._compat import Path


class TomlFile(BaseTOMLFile):
    def __init__(self, path):  # type: (Union[str, Path]) -> None
        super(TomlFile, self).__init__(str(path))

        self._path_ = Path(path)

    @property
    def path(self):  # type: () -> Path
        return self._path_

    def exists(self):  # type: () -> bool
        return self._path_.exists()

    def __getattr__(self, item):
        return getattr(self._path_, item)

    def __str__(self):
        return str(self._path)
