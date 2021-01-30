from typing import TYPE_CHECKING
from typing import List


if TYPE_CHECKING:
    from poetry.core.packages import Package  # noqa
    from poetry.core.packages import ProjectPackage  # noqa


class SolverResult:
    def __init__(
        self, root, packages, attempted_solutions
    ):  # type: ("ProjectPackage", List["Package"], int) -> None
        self._root = root
        self._packages = packages
        self._attempted_solutions = attempted_solutions

    @property
    def packages(self):  # type: () -> List["Package"]
        return self._packages

    @property
    def attempted_solutions(self):  # type: () -> int
        return self._attempted_solutions
