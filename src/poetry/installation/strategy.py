from __future__ import annotations

from enum import Enum


class Strategy(Enum):
    LATEST = "latest"
    LOWEST = "lowest"

    @classmethod
    def is_using_lowest(cls, other: Strategy | str) -> bool:
        if isinstance(other, cls):
            return other == cls.LOWEST
        else:
            return other == "lowest"
