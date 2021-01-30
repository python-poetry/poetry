from typing import TYPE_CHECKING
from typing import Optional

from .operation import Operation


if TYPE_CHECKING:
    from poetry.core.packages import Package  # noqa


class Install(Operation):
    def __init__(
        self, package, reason=None, priority=0
    ):  # type: ("Package", Optional[str], int) -> None
        super(Install, self).__init__(reason, priority=priority)

        self._package = package

    @property
    def package(self):  # type: () -> "Package"
        return self._package

    @property
    def job_type(self):  # type: () -> str
        return "install"

    def __str__(self):  # type: () -> str
        return "Installing {} ({})".format(
            self.package.pretty_name, self.format_version(self.package)
        )

    def __repr__(self):  # type: () -> str
        return "<Install {} ({})>".format(
            self.package.pretty_name, self.format_version(self.package)
        )
