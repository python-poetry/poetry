from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from poetry.config.config_source import ConfigSource
from poetry.config.config_source import PropertyNotFoundError
from poetry.config.config_source import split_key


if TYPE_CHECKING:
    from collections.abc import Sequence


class DictConfigSource(ConfigSource):
    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    @property
    def config(self) -> dict[str, Any]:
        return self._config

    def get_property(self, key: str | Sequence[str]) -> Any:
        keys = split_key(key)
        config = self._config

        for i, sub_key in enumerate(keys):
            if sub_key not in config:
                raise PropertyNotFoundError(f"Key {'.'.join(keys)} not in config")

            if i == len(keys) - 1:
                return config[sub_key]

            config = config[sub_key]

    def add_property(self, key: str | Sequence[str], value: Any) -> None:
        keys = split_key(key)
        config = self._config

        for i, sub_key in enumerate(keys):
            if sub_key not in config and i < len(keys) - 1:
                config[sub_key] = {}

            if i == len(keys) - 1:
                config[sub_key] = value
                break

            config = config[sub_key]

    def remove_property(self, key: str | Sequence[str]) -> None:
        keys = split_key(key)

        config = self._config
        for i, sub_key in enumerate(keys):
            if sub_key not in config:
                return

            if i == len(keys) - 1:
                del config[sub_key]

                break

            config = config[sub_key]
