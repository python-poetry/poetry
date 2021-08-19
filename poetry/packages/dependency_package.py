from typing import Any
from typing import List
from typing import Union

from poetry.core.packages.dependency import Dependency
from poetry.core.packages.package import Package


class DependencyPackage:
    def __init__(self, dependency: Dependency, package: Package) -> None:
        self._dependency = dependency
        self._package = package

    @property
    def dependency(self) -> Dependency:
        return self._dependency

    @property
    def package(self) -> Package:
        return self._package

    def clone(self) -> "DependencyPackage":
        return self.__class__(self._dependency, self._package.clone())

    def with_features(self, features: List[str]) -> "DependencyPackage":
        return self.__class__(self._dependency, self._package.with_features(features))

    def without_features(self) -> "DependencyPackage":
        return self.with_features([])

    def __getattr__(self, name: str) -> Any:
        return getattr(self._package, name)

    def __setattr__(self, key: str, value: Any) -> None:
        if key in {"_dependency", "_package"}:
            return super().__setattr__(key, value)

        setattr(self._package, key, value)

    def __str__(self) -> str:
        return str(self._package)

    def __repr__(self) -> str:
        return repr(self._package)

    def __hash__(self) -> int:
        return hash(self._package)

    def __eq__(self, other: Union[Package, "DependencyPackage"]) -> bool:
        if isinstance(other, DependencyPackage):
            other = other.package

        return self._package == other
