from typing import Union

from poetry.core.packages import Package

from .dependency_package import DependencyPackage


class PackageCollection(list):
    def __init__(self, dependency, packages=None):
        self._dependency = dependency

        if packages is None:
            packages = []

        super(PackageCollection, self).__init__()

        for package in packages:
            self.append(package)

    def append(self, package):  # type: (Union[Package, DependencyPackage]) -> None
        if isinstance(package, DependencyPackage):
            package = package.package

        package = DependencyPackage(self._dependency, package)

        return super(PackageCollection, self).append(package)
