from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.installation.base_installer import BaseInstaller


if TYPE_CHECKING:
    from poetry.core.packages.package import Package


class NoopInstaller(BaseInstaller):
    def __init__(self) -> None:
        self._installs: list[Package] = []
        self._updates: list[tuple[Package, Package]] = []
        self._removals: list[Package] = []

    @property
    def installs(self) -> list[Package]:
        return self._installs

    @property
    def updates(self) -> list[tuple[Package, Package]]:
        return self._updates

    @property
    def removals(self) -> list[Package]:
        return self._removals

    def install(self, package: Package) -> None:
        self._installs.append(package)

    def update(self, source: Package, target: Package) -> None:
        self._updates.append((source, target))

    def remove(self, package: Package) -> None:
        self._removals.append(package)
