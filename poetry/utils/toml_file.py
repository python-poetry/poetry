# -*- coding: utf-8 -*-
from tomlkit.toml_file import TOMLFile as BaseTOMLFile
from typing import Union

from ._compat import Path


class TomlFile(BaseTOMLFile):
    def __init__(self, path):  # type: (Union[str, Path]) -> None
        super(TomlFile, self).__init__(str(path))

        self._path_ = Path(path)

    @property
    def path(self):  # type: () -> Path
        return self._path_

    def __getattr__(self, item):
        return getattr(self._path_, item)
