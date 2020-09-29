# -*- coding: utf-8 -*-
import io
import os

from typing import Union

from tomlkit import loads
from tomlkit.toml_file import TOMLDocument
from tomlkit.toml_file import TOMLFile as BaseTOMLFile

from ._compat import Path


class TomlFile(BaseTOMLFile):
    def __init__(self, path):  # type: (Union[str, Path]) -> None
        super(TomlFile, self).__init__(str(path))

        self._path_ = Path(path)
        self._line_ending = os.linesep

    @property
    def path(self):  # type: () -> Path
        return self._path_

    def exists(self):  # type: () -> bool
        return self._path_.exists()

    def __getattr__(self, item):
        return getattr(self._path_, item)

    def __str__(self):
        return str(self._path)

    def read(self):  # type: () -> TOMLDocument
        try:
            with io.open(self._path, "rb") as f:
                first_line = f.read().splitlines(True)[0]
                if first_line.endswith(b"\r\n"):
                    self._line_ending = "\r\n"
                elif first_line.endswith(b"\r"):
                    self._line_ending = "\r"
                else:
                    self._line_ending = "\n"
        except IndexError:
            # empty file
            pass

        with io.open(self._path, encoding="utf-8") as f:
            return loads(f.read())

    def write(self, data):  # type: (TOMLDocument) -> None
        with io.open(self._path, "w", encoding="utf-8", newline=self._line_ending) as f:
            f.write(data.as_string())
