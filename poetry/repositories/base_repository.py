from typing import TYPE_CHECKING
from typing import List
from typing import Optional


if TYPE_CHECKING:
    from poetry.core.packages import Dependency  # noqa
    from poetry.core.packages import Package  # noqa


class BaseRepository(object):
    def __init__(self):  # type: () -> None
        self._packages = []

    @property
    def packages(self):  # type: () -> List["Package"]
        return self._packages

    def has_package(self, package):  # type: ("Package") -> None
        raise NotImplementedError()

    def package(
        self, name, version, extras=None
    ):  # type: (str, str, Optional[List[str]]) -> None
        raise NotImplementedError()

    def find_packages(self, dependency):  # type: ("Dependency") -> None
        raise NotImplementedError()

    def search(self, query):  # type: (str) -> None
        raise NotImplementedError()
