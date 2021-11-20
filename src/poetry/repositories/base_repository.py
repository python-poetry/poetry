from typing import TYPE_CHECKING
from typing import List
from typing import Optional


if TYPE_CHECKING:
    from poetry.core.packages.dependency import Dependency
    from poetry.core.packages.package import Package


class BaseRepository:
    def __init__(self) -> None:
        self._packages: List["Package"] = []

    @property
    def packages(self) -> List["Package"]:
        return self._packages

    def has_package(self, package: "Package") -> bool:
        raise NotImplementedError()

    def package(
        self, name: str, version: str, extras: Optional[List[str]] = None
    ) -> "Package":
        raise NotImplementedError()

    def find_packages(self, dependency: "Dependency") -> List["Package"]:
        raise NotImplementedError()

    def search(self, query: str) -> List["Package"]:
        raise NotImplementedError()
