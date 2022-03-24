from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from poetry.core.packages.dependency import Dependency
    from poetry.core.packages.package import Package


class BaseRepository:
    def __init__(self) -> None:
        self._packages: list[Package] = []

    @property
    def packages(self) -> list[Package]:
        return self._packages

    def has_package(self, package: Package) -> bool:
        raise NotImplementedError()

    def package(
        self, name: str, version: str, extras: list[str] | None = None
    ) -> Package:
        raise NotImplementedError()

    def find_packages(self, dependency: Dependency) -> list[Package]:
        raise NotImplementedError()

    def search(self, query: str) -> list[Package]:
        raise NotImplementedError()
