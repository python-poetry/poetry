from typing import TYPE_CHECKING
from typing import Optional

from .operation import Operation


if TYPE_CHECKING:
    from poetry.core.packages import Package  # noqa


class Uninstall(Operation):
    def __init__(
        self, package, reason=None, priority=float("inf")
    ):  # type: ("Package", Optional[str], int) -> None
        super(Uninstall, self).__init__(reason, priority=priority)

        self._package = package

    @property
    def package(self):  # type: () -> "Package"
        return self._package

    @property
    def job_type(self):  # type: () -> str
        return "uninstall"

    def __str__(self):  # type: () -> str
        return "Uninstalling {} ({})".format(
            self.package.pretty_name, self.format_version(self._package)
        )

    def __repr__(self):  # type: () -> str
        return "<Uninstall {} ({})>".format(
            self.package.pretty_name, self.format_version(self.package)
        )
