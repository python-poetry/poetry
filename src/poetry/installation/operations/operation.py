from typing import TYPE_CHECKING
from typing import Optional
from typing import TypeVar
from typing import Union


if TYPE_CHECKING:
    from poetry.core.packages.package import Package

T = TypeVar("T", bound="Operation")


class Operation:
    def __init__(
        self, reason: Optional[str] = None, priority: Union[int, float] = 0
    ) -> None:
        self._reason = reason

        self._skipped = False
        self._skip_reason: Optional[str] = None
        self._priority = priority

    @property
    def job_type(self) -> str:
        raise NotImplementedError

    @property
    def reason(self) -> Optional[str]:
        return self._reason

    @property
    def skipped(self) -> bool:
        return self._skipped

    @property
    def skip_reason(self) -> Optional[str]:
        return self._skip_reason

    @property
    def priority(self) -> Union[float, int]:
        return self._priority

    @property
    def package(self) -> "Package":
        raise NotImplementedError()

    def format_version(self, package: "Package") -> str:
        return package.full_pretty_version

    def skip(self: T, reason: str) -> T:
        self._skipped = True
        self._skip_reason = reason

        return self

    def unskip(self: T) -> T:
        self._skipped = False
        self._skip_reason = None

        return self
