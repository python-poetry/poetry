from __future__ import annotations

import dataclasses
import json

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Any

from cleo.io.null_io import NullIO


if TYPE_CHECKING:
    from collections.abc import Sequence

    from cleo.io.io import IO


UNSET = object()


def split_key(key: str | Sequence[str]) -> list[str]:
    """Split a config key into its component parts.

    If the key is a string, split on periods.

    If the key contains segments with periods
    (e.g. repository names like "my.repo"),
    this should be handled before calling this function
    so that a list or tuple of the segments is passed.
    """
    if isinstance(key, str):
        return key.split(".")
    return list(key)


class PropertyNotFoundError(ValueError):
    pass


class ConfigSource(ABC):
    @abstractmethod
    def get_property(self, key: str | Sequence[str]) -> Any: ...

    @abstractmethod
    def add_property(self, key: str | Sequence[str], value: Any) -> None: ...

    @abstractmethod
    def remove_property(self, key: str | Sequence[str]) -> None: ...


@dataclasses.dataclass
class ConfigSourceMigration:
    old_key: str
    new_key: str | None
    value_migration: dict[Any, Any] = dataclasses.field(default_factory=dict)

    def dry_run(self, config_source: ConfigSource, io: IO | None = None) -> bool:
        io = io or NullIO()

        try:
            old_value = config_source.get_property(self.old_key)
        except PropertyNotFoundError:
            return False

        new_value = (
            self.value_migration[old_value] if self.value_migration else old_value
        )

        msg = f"<c1>{self.old_key}</c1> = <c2>{json.dumps(old_value)}</c2>"

        if self.new_key is not None and new_value is not UNSET:
            msg += f" -> <c1>{self.new_key}</c1> = <c2>{json.dumps(new_value)}</c2>"
        elif self.new_key is None:
            msg += " -> <c1>Removed from config</c1>"
        elif self.new_key and new_value is UNSET:
            msg += f" -> <c1>{self.new_key}</c1> = <c2>Not explicit set</c2>"

        io.write_line(msg)

        return True

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
