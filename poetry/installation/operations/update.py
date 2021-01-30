from typing import TYPE_CHECKING
from typing import Optional

from .operation import Operation


if TYPE_CHECKING:
    from poetry.core.packages import Package  # noqa


class Update(Operation):
    def __init__(
        self, initial, target, reason=None, priority=0
    ):  # type: ("Package", "Package", Optional[str], int) -> None
        self._initial_package = initial
        self._target_package = target

        super(Update, self).__init__(reason, priority=priority)

    @property
    def initial_package(self):  # type: () -> "Package"
        return self._initial_package

    @property
    def target_package(self):  # type: () -> "Package"
        return self._target_package

    @property
    def package(self):  # type: () -> "Package"
        return self._target_package

    @property
    def job_type(self):  # type: () -> str
        return "update"

    def __str__(self):  # type: () -> str
        return "Updating {} ({}) to {} ({})".format(
            self.initial_package.pretty_name,
            self.format_version(self.initial_package),
            self.target_package.pretty_name,
            self.format_version(self.target_package),
        )

    def __repr__(self):  # type: () -> str
        return "<Update {} ({}) to {} ({})>".format(
            self.initial_package.pretty_name,
            self.format_version(self.initial_package),
            self.target_package.pretty_name,
            self.format_version(self.target_package),
        )
