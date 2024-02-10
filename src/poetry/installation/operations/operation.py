from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TypeVar


if TYPE_CHECKING:
    from poetry.core.packages.package import Package

T = TypeVar("T", bound="Operation")


class Operation:
    def __init__(self, reason: str | None = None, priority: float = 0) -> None:
        self._reason = reason

        self._skipped = False
        self._skip_reason: str | None = None
        self._priority = priority

    @property
    def job_type(self) -> str:
        raise NotImplementedError

    @property
    def reason(self) -> str | None:
        return self._reason

    @property
    def skipped(self) -> bool:
        return self._skipped

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason

    @property
    def priority(self) -> float:
        return self._priority

    @property
    def package(self) -> Package:
        raise NotImplementedError()

    def format_version(self, package: Package) -> str:
        version: str = package.full_pretty_version
        return version

    def skip(self: T, reason: str) -> T:
        self._skipped = True
        self._skip_reason = reason

        return self

    def unskip(self: T) -> T:
        self._skipped = False
        self._skip_reason = None

        return self
