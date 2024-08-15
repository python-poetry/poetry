from enum import Enum

from typing_extensions import Self


class Strategy(Enum):
    LATEST = "latest"
    LOWEST = "lowest"

    @classmethod
    def is_using_lowest(cls, other: Self | str) -> bool:
        if isinstance(other, cls):
            return other == cls.LOWEST
        else:
            return other == "lowest"
