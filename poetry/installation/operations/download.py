from typing import TYPE_CHECKING
from typing import Optional

from .operation import Operation


if TYPE_CHECKING:
    from poetry.core.packages.package import Package


class Download(Operation):
    def __init__(
        self, package: "Package", reason: Optional[str] = None, priority: int = 0
    ) -> None:
        super(Download, self).__init__(reason, priority=priority)

        self._package = package

    @property
    def package(self) -> "Package":
        return self._package

    @property
    def job_type(self) -> str:
        return "download"

    def __str__(self) -> str:
        return "Downloading {} ({})".format(
            self.package.pretty_name, self.format_version(self.package)
        )

    def __repr__(self) -> str:
        return "<Download {} ({})>".format(
            self.package.pretty_name, self.format_version(self.package)
        )
