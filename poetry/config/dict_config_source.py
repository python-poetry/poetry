from typing import Any
from typing import Dict

from .config_source import ConfigSource


class DictConfigSource(ConfigSource):
    def __init__(self):  # type: () -> None
        self._config = {}

    @property
    def config(self):  # type: () -> Dict[str, Any]
        return self._config

    def add_property(self, key, value):  # type: (str, Any) -> None
        keys = key.split(".")
        config = self._config

        for i, key in enumerate(keys):
            if key not in config and i < len(keys) - 1:
                config[key] = {}

            if i == len(keys) - 1:
                config[key] = value
                break

            config = config[key]

    def remove_property(self, key):  # type: (str) -> None
        keys = key.split(".")

        config = self._config
        for i, key in enumerate(keys):
            if key not in config:
                return

            if i == len(keys) - 1:
                del config[key]

                break

            config = config[key]
