from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any


class ConfigSource(ABC):
    @abstractmethod
    def add_property(self, key: str, value: Any) -> None: ...

    @abstractmethod
    def remove_property(self, key: str) -> None: ...
