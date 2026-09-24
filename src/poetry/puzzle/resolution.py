from __future__ import annotations

from enum import Enum


class ResolutionStrategy(str, Enum):
    HIGHEST = "highest"
    LOWEST = "lowest"
    LOWEST_DIRECT = "lowest-direct"


def parse_resolution_strategy(value: str) -> ResolutionStrategy:
    try:
        return ResolutionStrategy(value)
    except ValueError as error:
        allowed = ", ".join(strategy.value for strategy in ResolutionStrategy)
        raise ValueError(
            f"Invalid resolution strategy '{value}'. Expected one of: {allowed}."
        ) from error
