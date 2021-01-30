from typing import TYPE_CHECKING
from typing import List
from typing import Union

from .dependency_package import DependencyPackage


if TYPE_CHECKING:
    from poetry.core.packages import Dependency  # noqa
    from poetry.core.packages import Package  # noqa


class PackageCollection(list):
    def __init__(
        self, dependency, packages=None
    ):  # type: (Dependency, List[Union["Package", DependencyPackage]]) -> None
        self._dependency = dependency

        if packages is None:
            packages = []

        super(PackageCollection, self).__init__()

        for package in packages:
            self.append(package)

    def append(self, package):  # type: (Union["Package", DependencyPackage]) -> None
        if isinstance(package, DependencyPackage):
            package = package.package

        package = DependencyPackage(self._dependency, package)

        return super(PackageCollection, self).append(package)
