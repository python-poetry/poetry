from contextlib import contextmanager
from typing import Any

from tomlkit import document
from tomlkit import table

from poetry.utils.toml_file import TomlFile

from .config_source import ConfigSource


class FileConfigSource(ConfigSource):
    def __init__(self, file, auth_config=False):  # type: (TomlFile, bool) -> None
        self._file = file
        self._auth_config = auth_config

    @property
    def name(self):  # type: () -> str
        return str(self._file.path)

    @property
    def file(self):  # type: () -> TomlFile
        return self._file

    def add_property(self, key, value):  # type: (str, Any) -> None
        with self.secure() as config:
            keys = key.split(".")

            for i, key in enumerate(keys):
                if key not in config and i < len(keys) - 1:
                    config[key] = table()

                if i == len(keys) - 1:
                    config[key] = value
                    break

                config = config[key]

    def remove_property(self, key):  # type: (str) -> None
        with self.secure() as config:
            keys = key.split(".")

            current_config = config
            for i, key in enumerate(keys):
                if key not in current_config:
                    return

                if i == len(keys) - 1:
                    del current_config[key]

                    break

                current_config = current_config[key]

    @contextmanager
    def secure(self):
        if self.file.exists():
            initial_config = self.file.read()
            config = self.file.read()
        else:
            initial_config = document()
            config = document()

        new_file = not self.file.exists()

        yield config

        try:
            # Ensuring the file is only readable and writable
            # by the current user
            mode = 0o600

            if new_file:
                self.file.touch(mode=mode)

            self.file.write(config)
        except Exception:
            self.file.write(initial_config)

            raise
