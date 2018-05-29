from typing import Any

from .incompatibility import Incompatibility
from .term import Term


class Assignment(Term):
    """
    A term in a PartialSolution that tracks some additional metadata.
    """

    def __init__(self, dependency, is_positive, decision_level, index, cause=None):
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
    def cause(self):  # type: () -> Incompatibility
        return self._cause

    @classmethod
    def decision(
        cls, package, decision_level, index
    ):  # type: (Any, int, int) -> Assignment
        return cls(package.to_dependency(), True, decision_level, index)

    @classmethod
    def derivation(
        cls, dependency, is_positive, cause, decision_level, index
    ):  # type: (Any, bool, Incompatibility, int, int) -> Assignment
        return cls(dependency, is_positive, decision_level, index, cause)

    def is_decision(self):  # type: () -> bool
        return self._cause is None
