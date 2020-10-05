from collections import OrderedDict
from typing import Dict
from typing import List

from poetry.core.packages import Dependency
from poetry.core.packages import Package

from .assignment import Assignment
from .incompatibility import Incompatibility
from .set_relation import SetRelation
from .term import Term


class PartialSolution:
    """
    # A list of Assignments that represent the solver's current best guess about
    # what's true for the eventual set of package versions that will comprise the
    # total solution.
    #
    # See https://github.com/dart-lang/mixology/tree/master/doc/solver.md#partial-solution.
    """

    def __init__(self):
        # The assignments that have been made so far, in the order they were
        # assigned.
        self._assignments = []  # type: List[Assignment]

        # The decisions made for each package.
        self._decisions = OrderedDict()  # type: Dict[str, Package]

        # The intersection of all positive Assignments for each package, minus any
        # negative Assignments that refer to that package.
        #
        # This is derived from self._assignments.
        self._positive = OrderedDict()  # type: Dict[str, Term]

        # The union of all negative Assignments for each package.
        #
        # If a package has any positive Assignments, it doesn't appear in this
        # map.
        #
        # This is derived from self._assignments.
        self._negative = OrderedDict()  # type: Dict[str, Dict[str, Term]]

        # The number of distinct solutions that have been attempted so far.
        self._attempted_solutions = 1

        # Whether the solver is currently backtracking.
        self._backtracking = False

    @property
    def decisions(self):  # type: () -> List[Package]
        return list(self._decisions.values())

    @property
    def decision_level(self):  # type: () -> int
        return len(self._decisions)

    @property
    def attempted_solutions(self):  # type: () -> int
        return self._attempted_solutions

    @property
    def unsatisfied(self):  # type: () -> List[Dependency]
        return [
            term.dependency
            for term in self._positive.values()
            if term.dependency.complete_name not in self._decisions
        ]

    def decide(self, package):  # type: (Package) -> None
        """
        Adds an assignment of package as a decision
        and increments the decision level.
        """
        # When we make a new decision after backtracking, count an additional
        # attempted solution. If we backtrack multiple times in a row, though, we
        # only want to count one, since we haven't actually started attempting a
        # new solution.
        if self._backtracking:
            self._attempted_solutions += 1

        self._backtracking = False
        self._decisions[package.complete_name] = package

        self._assign(
            Assignment.decision(package, self.decision_level, len(self._assignments))
        )

    def derive(
        self, dependency, is_positive, cause
    ):  # type: (Dependency, bool, Incompatibility) -> None
        """
        Adds an assignment of package as a derivation.
        """
        self._assign(
            Assignment.derivation(
                dependency,
                is_positive,
                cause,
                self.decision_level,
                len(self._assignments),
            )
        )

    def _assign(self, assignment):  # type: (Assignment) -> None
        """
        Adds an Assignment to _assignments and _positive or _negative.
        """
        self._assignments.append(assignment)
        self._register(assignment)

    def backtrack(self, decision_level):  # type: (int) -> None
        """
        Resets the current decision level to decision_level, and removes all
        assignments made after that level.
        """
        self._backtracking = True

        packages = set()
        while self._assignments[-1].decision_level > decision_level:
            removed = self._assignments.pop(-1)
            packages.add(removed.dependency.complete_name)
            if removed.is_decision():
                del self._decisions[removed.dependency.complete_name]

        # Re-compute _positive and _negative for the packages that were removed.
        for package in packages:
            if package in self._positive:
                del self._positive[package]

            if package in self._negative:
                del self._negative[package]

        for assignment in self._assignments:
            if assignment.dependency.complete_name in packages:
                self._register(assignment)

    def _register(self, assignment):  # type: (Assignment) -> None
        """
        Registers an Assignment in _positive or _negative.
        """
        name = assignment.dependency.complete_name
        old_positive = self._positive.get(name)
        if old_positive is not None:
            self._positive[name] = old_positive.intersect(assignment)

            return

        ref = assignment.dependency.complete_name
        negative_by_ref = self._negative.get(name)
        old_negative = None if negative_by_ref is None else negative_by_ref.get(ref)
        if old_negative is None:
            term = assignment
        else:
            term = assignment.intersect(old_negative)

        if term.is_positive():
            if name in self._negative:
                del self._negative[name]

            self._positive[name] = term
        else:
            if name not in self._negative:
                self._negative[name] = {}

            self._negative[name][ref] = term

    def satisfier(self, term):  # type: (Term) -> Assignment
        """
        Returns the first Assignment in this solution such that the sublist of
        assignments up to and including that entry collectively satisfies term.
        """
        assigned_term = None  # type: Term

        for assignment in self._assignments:
            if assignment.dependency.complete_name != term.dependency.complete_name:
                continue

            if (
                not assignment.dependency.is_root
                and not assignment.dependency.is_same_package_as(term.dependency)
            ):
                if not assignment.is_positive():
                    continue

                assert not term.is_positive()

                return assignment

            if assigned_term is None:
                assigned_term = assignment
            else:
                assigned_term = assigned_term.intersect(assignment)

            # As soon as we have enough assignments to satisfy term, return them.
            if assigned_term.satisfies(term):
                return assignment

        raise RuntimeError("[BUG] {} is not satisfied.".format(term))

    def satisfies(self, term):  # type: (Term) -> bool
        return self.relation(term) == SetRelation.SUBSET

    def relation(self, term):  # type: (Term) -> int
        positive = self._positive.get(term.dependency.complete_name)
        if positive is not None:
            return positive.relation(term)

        by_ref = self._negative.get(term.dependency.complete_name)
        if by_ref is None:
            return SetRelation.OVERLAPPING

        negative = by_ref[term.dependency.complete_name]
        if negative is None:
            return SetRelation.OVERLAPPING

        return negative.relation(term)
