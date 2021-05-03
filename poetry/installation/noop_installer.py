from typing import TYPE_CHECKING
from typing import List

from .base_installer import BaseInstaller


if TYPE_CHECKING:
    from poetry.core.packages.package import Package


class NoopInstaller(BaseInstaller):
    def __init__(self) -> None:
        self._installs = []
        self._updates = []
        self._removals = []

    @property
    def installs(self) -> List["Package"]:
        return self._installs

    @property
    def updates(self) -> List["Package"]:
        return self._updates

    @property
    def removals(self) -> List["Package"]:
        return self._removals

    def install(self, package: "Package") -> None:
        self._installs.append(package)

    def update(self, source: "Package", target: "Package") -> None:
        self._updates.append((source, target))

    def remove(self, package: "Package") -> None:
        self._removals.append(package)
