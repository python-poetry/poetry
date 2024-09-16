from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TypeVar


if TYPE_CHECKING:
    from typing import ClassVar

    from poetry.core.packages.package import Package


T = TypeVar("T", bound="Operation")


class Operation:
    _message_default_color: ClassVar[str] = "c2"
    _message_package_color: ClassVar[str] = "c1"

    def __init__(self, reason: str | None = None, priority: float = 0) -> None:
        self._reason = reason

        self.error = False
        self.warning = False
        self.done = False
        self._skipped = False
        self._skip_reason: str | None = None
        self._priority = priority

    @property
    def _message_base_tag(self) -> str:
        return "fg=default" + ";options=dark" * self.skipped

    @property
    def _message_color(self) -> str:
        color = self._message_default_color
        if self.error:
            color = "error"
        elif self.warning:
            color = "warning"
        elif self.done:
            color = "success"
        return color + "_dark" * self.skipped

    def get_message(self) -> str:
        return ""

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
