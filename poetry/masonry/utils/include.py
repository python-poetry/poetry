from typing import List

from poetry.utils._compat import Path


class Include(object):
    """
    Represents an "include" entry.

    It can be a glob string, a single file or a directory.

    This class will then detect the type of this include:

        - a package
        - a module
        - a file
        - a directory
    """

    def __init__(self, base, include):  # type: (Path, str) -> None
        self._base = base
        self._include = str(include)

        self._elements = sorted(list(self._base.glob(self._include)))

    @property
    def base(self):  # type: () -> Path
        return self._base

    @property
    def elements(self):  # type: () -> List[Path]
        return self._elements

    def is_empty(self):  # type: () -> bool
        return len(self._elements) == 0

    def refresh(self):  # type: () -> Include
        self._elements = sorted(list(self._base.glob(self._include)))

        return self
