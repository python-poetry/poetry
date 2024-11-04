from __future__ import annotations

import dataclasses

from abc import ABC
from abc import abstractmethod
from typing import Any


UNSET = object()


class PropertyNotFoundError(ValueError):
    pass


class ConfigSource(ABC):
    @abstractmethod
    def get_property(self, key: str) -> Any: ...

    @abstractmethod
    def add_property(self, key: str, value: Any) -> None: ...

    @abstractmethod
    def remove_property(self, key: str) -> None: ...


@dataclasses.dataclass
class ConfigSourceMigration:
    old_key: str
    new_key: str | None
    value_migration: dict[Any, Any] = dataclasses.field(default_factory=dict)

    def apply(self, config_source: ConfigSource) -> None:
        try:
            old_value = config_source.get_property(self.old_key)
        except PropertyNotFoundError:
            return

        new_value = (
            self.value_migration[old_value] if self.value_migration else old_value
        )

        config_source.remove_property(self.old_key)

        if self.new_key is not None and new_value is not UNSET:
            config_source.add_property(self.new_key, new_value)


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
