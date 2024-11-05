from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any


class PropertyNotFoundError(ValueError):
    pass


class ConfigSource(ABC):
    @abstractmethod
    def get_property(self, key: str) -> Any: ...

    @abstractmethod
    def add_property(self, key: str, value: Any) -> None: ...

    @abstractmethod
    def remove_property(self, key: str) -> None: ...


def drop_empty_config_category(
    keys: list[str], config: dict[Any, Any]
) -> dict[Any, Any]:
    config_ = {}

    for key, value in config.items():
        if not keys or key != keys[0]:
            config_[key] = value
            continue
        if keys and key == keys[0]:
            if isinstance(value, dict):
                value = drop_empty_config_category(keys[1:], value)

            if value != {}:
                config_[key] = value

    return config_
