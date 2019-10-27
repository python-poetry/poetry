from typing import List
from typing import Optional

from poetry.utils._compat import Path
from poetry.utils._compat import glob


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

    def __init__(
        self, base, include, formats=None
    ):  # type: (Path, str, Optional[List[str]]) -> None
        self._base = base
        self._include = str(include)
        self._formats = formats

        self._elements = sorted(list(self._glob_include()))

    @property
    def base(self):  # type: () -> Path
        return self._base

    @property
    def elements(self):  # type: () -> List[Path]
        return self._elements

    @property
    def formats(self):  # type: () -> Optional[List[str]]
        return self._formats

    def is_empty(self):  # type: () -> bool
        return len(self._elements) == 0

    def refresh(self):  # type: () -> Include
        self._elements = sorted(list(self._glob_include()))

        return self

    def _glob_include(self):
        element_paths_string = list(
            glob(str(self._base) + "/" + self._include, recursive=True)
        )
        return map(lambda path_string: Path(path_string), element_paths_string)
