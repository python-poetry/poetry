from __future__ import absolute_import

import io
import os

from typing import Any

from tomlkit import document
from tomlkit import table

from .locations import CONFIG_DIR
from .utils._compat import Path
from .utils.toml_file import TomlFile


class Config:
    def __init__(self, file):  # type: (TomlFile) -> None
        self._file = file
        if not self._file.exists():
            self._content = document()
        else:
            self._content = file.read()

    @property
    def name(self):
        return str(self._file.path)

    @property
    def file(self):
        return self._file

    @property
    def content(self):
        return self._content

    def setting(self, setting_name, default=None):  # type: (str) -> Any
        """
        Retrieve a setting value.
        """
        keys = setting_name.split(".")

        config = self._content
        for key in keys:
            if key not in config:
                return default

            config = config[key]

        return config

    def add_property(self, key, value):
        keys = key.split(".")

        config = self._content
        for i, key in enumerate(keys):
            if key not in config and i < len(keys) - 1:
                config[key] = table()

            if i == len(keys) - 1:
                config[key] = value
                break

            config = config[key]

        self.dump()

    def remove_property(self, key):
        keys = key.split(".")

        config = self._content
        for i, key in enumerate(keys):
            if key not in config:
                return

            if i == len(keys) - 1:
                del config[key]
                break

            config = config[key]

        self.dump()

    def dump(self):
        # Ensuring the file is only readable and writable
        # by the current user
        mode = 0o600
        umask = 0o777 ^ mode

        if self._file.exists():
            # If the file already exists, remove it
            # if the permissions are higher than what we want
            current_mode = os.stat(str(self._file)).st_mode & 0o777
            if current_mode != 384:
                os.remove(str(self._file))

        if self._file.exists():
            fd = str(self._file)
        else:
            umask_original = os.umask(umask)
            try:
                fd = os.open(str(self._file), os.O_WRONLY | os.O_CREAT, mode)
            finally:
                os.umask(umask_original)

        with io.open(fd, "w", encoding="utf-8") as f:
            f.write(self._content.as_string())

    @classmethod
    def create(cls, file, base_dir=None):  # type: (...) -> Config
        if base_dir is None:
            base_dir = CONFIG_DIR

        file = TomlFile(Path(base_dir) / file)

        return cls(file)
