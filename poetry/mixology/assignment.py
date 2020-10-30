from typing import TYPE_CHECKING
from typing import Any
from typing import Optional

from .term import Term


if TYPE_CHECKING:
    from poetry.core.packages import Dependency  # noqa
    from poetry.core.packages import Package  # noqa

    from .incompatibility import Incompatibility  # noqa


class Assignment(Term):
    """
    A term in a PartialSolution that tracks some additional metadata.
    """

    def __init__(
        self, dependency, is_positive, decision_level, index, cause=None
    ):  # type: ("Dependency", bool, int, int, Optional["Incompatibility"]) -> None
        super(Assignment, self).__init__(dependency, is_positive)

        self._decision_level = decision_level
        self._index = index
        self._cause = cause

    @property
    def decision_level(self):  # type: () -> int
        return self._decision_level

    @property
    def index(self):  # type: () -> int
        return self._index

    @property
    def cause(self):  # type: () -> "Incompatibility"
        return self._cause

    @classmethod
    def decision(
        cls, package, decision_level, index
    ):  # type: ("Package", int, int) -> Assignment
        return cls(package.to_dependency(), True, decision_level, index)

    @classmethod
    def derivation(
        cls, dependency, is_positive, cause, decision_level, index
    ):  # type: (Any, bool, "Incompatibility", int, int) -> "Assignment"
        return cls(dependency, is_positive, decision_level, index, cause)

    def is_decision(self):  # type: () -> bool
        return self._cause is None
