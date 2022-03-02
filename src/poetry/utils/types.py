from __future__ import annotations

from typing import Protocol
from typing import TypedDict


class Auth(TypedDict):
    username: str
    password: str | None


class Writer(Protocol):
    def write(self, text: str) -> None:
        pass
