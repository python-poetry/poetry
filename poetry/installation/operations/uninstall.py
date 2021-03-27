from typing import TYPE_CHECKING
from typing import Optional

from .operation import Operation


if TYPE_CHECKING:
    from poetry.core.packages.package import Package


class Uninstall(Operation):
    def __init__(
        self,
        package: "Package",
        reason: Optional[str] = None,
        priority: int = float("inf"),
    ) -> None:
        super(Uninstall, self).__init__(reason, priority=priority)

        self._package = package

    @property
    def package(self) -> "Package":
        return self._package

    @property
    def job_type(self) -> str:
        return "uninstall"

    def __str__(self) -> str:
        return "Uninstalling {} ({})".format(
            self.package.pretty_name, self.format_version(self._package)
        )

    def __repr__(self) -> str:
        return "<Uninstall {} ({})>".format(
            self.package.pretty_name, self.format_version(self.package)
        )
