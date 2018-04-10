from typing import Any

from .locations import CONFIG_DIR
from .utils._compat import Path
from .utils.toml_file import TomlFile
from .utils.toml_file import TOMLFile


class Config:

    def __init__(self, file):  # type: (TomlFile) -> None
        self._file = file
        if not self._file.exists():
            self._raw_content = {}
            self._content = TOMLFile([])
        else:
            self._raw_content = file.read(raw=True)
            self._content = file.read()
        
    @property
    def name(self):
        return str(self._file.path)

    @property
    def file(self):
        return self._file

    @property
    def raw_content(self):
        return self._raw_content

    @property
    def content(self):
        return self._content

    def setting(self, setting_name, default=None):  # type: (str) -> Any
        """
        Retrieve a setting value.
        """
        keys = setting_name.split('.')

        config = self._raw_content
        for key in keys:
            if key not in config:
                return default

            config = config[key]

        return config

    def add_property(self, key, value):
        keys = key.split('.')

        config = self._content
        for i, key in enumerate(keys):
            if key not in config and i < len(keys) - 1:
                config[key] = {}

            if i == len(keys) - 1:
                config[key] = value
                break

            config = config[key]

        self.dump()

    def remove_property(self, key):
        keys = key.split('.')

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
        self._file.write(self._content)

    @classmethod
    def create(cls, file, base_dir=None):  # type: (...) -> Config
        if base_dir is None:
            base_dir = CONFIG_DIR

        file = TomlFile(Path(base_dir) / file)

        return cls(file)
