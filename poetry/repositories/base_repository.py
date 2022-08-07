from typing import List
from typing import Optional

from poetry.core.packages.package import Package


class BaseRepository(object):
    def __init__(self):
        self._packages = []  # type: List[Package]

    @property
    def packages(self):  # type: () -> List[Package]
        return self._packages

    def has_package(self, package):
        raise NotImplementedError()

    def package(
        self, name, version, extras=None
    ):  # type: (str, str, Optional[List[str]]) -> Package
        raise NotImplementedError()

    def find_packages(self, dependency):
        raise NotImplementedError()

    def search(self, query):
        raise NotImplementedError()
