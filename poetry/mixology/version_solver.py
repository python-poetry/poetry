# -*- coding: utf-8 -*-
import time

from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import List
from typing import Union

from poetry.core.packages import Dependency
from poetry.core.packages import Package
from poetry.core.packages import ProjectPackage
from poetry.core.semver import Version
from poetry.core.semver import VersionRange

from .failure import SolveFailure
from .incompatibility import Incompatibility
from .incompatibility_cause import ConflictCause
from .incompatibility_cause import NoVersionsCause
from .incompatibility_cause import PackageNotFoundCause
from .incompatibility_cause import RootCause
from .partial_solution import PartialSolution
from .result import SolverResult
from .set_relation import SetRelation
from .term import Term


if TYPE_CHECKING:
    from poetry.puzzle.provider import Provider


_conflict = object()


class VersionSolver:
    """
    The version solver that finds a set of package versions that satisfy the
    root package's dependencies.

    See https://github.com/dart-lang/pub/tree/master/doc/solver.md for details
    on how this solver works.
    """

    def __init__(
        self,
        root,  # type: ProjectPackage
        provider,  # type: Provider
        locked=None,  # type: Dict[str, Package]
        use_latest=None,  # type: List[str]
    ):
        self._root = root
        self._provider = provider
        self._locked = locked or {}

        if use_latest is None:
            use_latest = []

        self._use_latest = use_latest

        self._incompatibilities = {}  # type: Dict[str, List[Incompatibility]]
        self._solution = PartialSolution()

    @property
    def solution(self):  # type: () -> PartialSolution
        return self._solution

    def solve(self):  # type: () -> SolverResult
        """
        Finds a set of dependencies that match the root package's constraints,
        or raises an error if no such set is available.
        """
        start = time.time()
        root_dependency = Dependency(self._root.name, self._root.version)
        root_dependency.is_root = True

        self._add_incompatibility(
            Incompatibility([Term(root_dependency, False)], RootCause())
        )

        try:
            next = self._root.name
            while next is not None:
                self._propagate(next)
                next = self._choose_package_version()

            return self._result()
        except Exception:
            raise
        finally:
            self._log(
                "Version solving took {:.3f} seconds.\n"
                "Tried {} solutions.".format(
                    time.time() - start, self._solution.attempted_solutions
                )
            )

    def _propagate(self, package):  # type: (str) -> None
        """
        Performs unit propagation on incompatibilities transitively
        related to package to derive new assignments for _solution.
        """
        changed = set()
        changed.add(package)

        while changed:
            package = changed.pop()

            # Iterate in reverse because conflict resolution tends to produce more
            # general incompatibilities as time goes on. If we look at those first,
            # we can derive stronger assignments sooner and more eagerly find
            # conflicts.
            for incompatibility in reversed(self._incompatibilities[package]):
                result = self._propagate_incompatibility(incompatibility)

                if result is _conflict:
                    # If the incompatibility is satisfied by the solution, we use
                    # _resolve_conflict() to determine the root cause of the conflict as a
                    # new incompatibility.
                    #
                    # It also backjumps to a point in the solution
                    # where that incompatibility will allow us to derive new assignments
                    # that avoid the conflict.
                    root_cause = self._resolve_conflict(incompatibility)

                    # Back jumping erases all the assignments we did at the previous
                    # decision level, so we clear [changed] and refill it with the
                    # newly-propagated assignment.
                    changed.clear()
                    changed.add(str(self._propagate_incompatibility(root_cause)))
                    break
                elif result is not None:
                    changed.add(result)

    def _propagate_incompatibility(
        self, incompatibility
    ):  # type: (Incompatibility) -> Union[str, _conflict, None]
        """
        If incompatibility is almost satisfied by _solution, adds the
        negation of the unsatisfied term to _solution.

        If incompatibility is satisfied by _solution, returns _conflict. If
        incompatibility is almost satisfied by _solution, returns the
        unsatisfied term's package name.

        Otherwise, returns None.
        """
        # The first entry in incompatibility.terms that's not yet satisfied by
        # _solution, if one exists. If we find more than one, _solution is
        # inconclusive for incompatibility and we can't deduce anything.
        unsatisfied = None

        for term in incompatibility.terms:
            relation = self._solution.relation(term)

            if relation == SetRelation.DISJOINT:
                # If term is already contradicted by _solution, then
                # incompatibility is contradicted as well and there's nothing new we
                # can deduce from it.
                return
            elif relation == SetRelation.OVERLAPPING:
                # If more than one term is inconclusive, we can't deduce anything about
                # incompatibility.
                if unsatisfied is not None:
                    return

                # If exactly one term in incompatibility is inconclusive, then it's
                # almost satisfied and [term] is the unsatisfied term. We can add the
                # inverse of the term to _solution.
                unsatisfied = term

        # If *all* terms in incompatibility are satisfied by _solution, then
        # incompatibility is satisfied and we have a conflict.
        if unsatisfied is None:
            return _conflict

        self._log(
            "derived: {}{}".format(
                "not " if unsatisfied.is_positive() else "", unsatisfied.dependency
            )
        )

        self._solution.derive(
            unsatisfied.dependency, not unsatisfied.is_positive(), incompatibility
        )

        return unsatisfied.dependency.complete_name

    def _resolve_conflict(
        self, incompatibility
    ):  # type: (Incompatibility) -> Incompatibility
        """
        Given an incompatibility that's satisfied by _solution,
        The `conflict resolution`_ constructs a new incompatibility that encapsulates the root
        cause of the conflict and backtracks _solution until the new
        incompatibility will allow _propagate() to deduce new assignments.

        Adds the new incompatibility to _incompatibilities and returns it.

        .. _conflict resolution: https://github.com/dart-lang/pub/tree/master/doc/solver.md#conflict-resolution
        """
        self._log("conflict: {}".format(incompatibility))

        new_incompatibility = False
        while not incompatibility.is_failure():
            # The term in incompatibility.terms that was most recently satisfied by
            # _solution.
            most_recent_term = None

            # The earliest assignment in _solution such that incompatibility is
            # satisfied by _solution up to and including this assignment.
            most_recent_satisfier = None

            # The difference between most_recent_satisfier and most_recent_term;
            # that is, the versions that are allowed by most_recent_satisfier and not
            # by most_recent_term. This is None if most_recent_satisfier totally
            # satisfies most_recent_term.
            difference = None

            # The decision level of the earliest assignment in _solution *before*
            # most_recent_satisfier such that incompatibility is satisfied by
            # _solution up to and including this assignment plus
            # most_recent_satisfier.
            #
            # Decision level 1 is the level where the root package was selected. It's
            # safe to go back to decision level 0, but stopping at 1 tends to produce
            # better error messages, because references to the root package end up
            # closer to the final conclusion that no solution exists.
            previous_satisfier_level = 1

            for term in incompatibility.terms:
                satisfier = self._solution.satisfier(term)

                if most_recent_satisfier is None:
                    most_recent_term = term
                    most_recent_satisfier = satisfier
                elif most_recent_satisfier.index < satisfier.index:
                    previous_satisfier_level = max(
                        previous_satisfier_level, most_recent_satisfier.decision_level
                    )
                    most_recent_term = term
                    most_recent_satisfier = satisfier
                    difference = None
                else:
                    previous_satisfier_level = max(
                        previous_satisfier_level, satisfier.decision_level
                    )

                if most_recent_term == term:
                    # If most_recent_satisfier doesn't satisfy most_recent_term on its
                    # own, then the next-most-recent satisfier may be the one that
                    # satisfies the remainder.
                    difference = most_recent_satisfier.difference(most_recent_term)
                    if difference is not None:
                        previous_satisfier_level = max(
                            previous_satisfier_level,
                            self._solution.satisfier(difference.inverse).decision_level,
                        )

            # If most_recent_identifier is the only satisfier left at its decision
            # level, or if it has no cause (indicating that it's a decision rather
            # than a derivation), then incompatibility is the root cause. We then
            # backjump to previous_satisfier_level, where incompatibility is
            # guaranteed to allow _propagate to produce more assignments.
            if (
                previous_satisfier_level < most_recent_satisfier.decision_level
                or most_recent_satisfier.cause is None
            ):
                self._solution.backtrack(previous_satisfier_level)
                if new_incompatibility:
                    self._add_incompatibility(incompatibility)

                return incompatibility

            # Create a new incompatibility by combining incompatibility with the
            # incompatibility that caused most_recent_satisfier to be assigned. Doing
            # this iteratively constructs an incompatibility that's guaranteed to be
            # true (that is, we know for sure no solution will satisfy the
            # incompatibility) while also approximating the intuitive notion of the
            # "root cause" of the conflict.
            new_terms = []
            for term in incompatibility.terms:
                if term != most_recent_term:
                    new_terms.append(term)

            for term in most_recent_satisfier.cause.terms:
                if term.dependency != most_recent_satisfier.dependency:
                    new_terms.append(term)

            # The most_recent_satisfier may not satisfy most_recent_term on its own
            # if there are a collection of constraints on most_recent_term that
            # only satisfy it together. For example, if most_recent_term is
            # `foo ^1.0.0` and _solution contains `[foo >=1.0.0,
            # foo <2.0.0]`, then most_recent_satisfier will be `foo <2.0.0` even
            # though it doesn't totally satisfy `foo ^1.0.0`.
            #
            # In this case, we add `not (most_recent_satisfier \ most_recent_term)` to
            # the incompatibility as well, See the `algorithm documentation`_ for
            # details.
            #
            # .. _algorithm documentation: https://github.com/dart-lang/pub/tree/master/doc/solver.md#conflict-resolution
            if difference is not None:
                new_terms.append(difference.inverse)

            incompatibility = Incompatibility(
                new_terms, ConflictCause(incompatibility, most_recent_satisfier.cause)
            )
            new_incompatibility = True

            partially = "" if difference is None else " partially"
            bang = "!"
            self._log(
                "{} {} is{} satisfied by {}".format(
                    bang, most_recent_term, partially, most_recent_satisfier
                )
            )
            self._log(
                '{} which is caused by "{}"'.format(bang, most_recent_satisfier.cause)
            )
            self._log("{} thus: {}".format(bang, incompatibility))

        raise SolveFailure(incompatibility)

    def _choose_package_version(self):  # type: () -> Union[str, None]
        """
        Tries to select a version of a required package.

        Returns the name of the package whose incompatibilities should be
        propagated by _propagate(), or None indicating that version solving is
        complete and a solution has been found.
        """
        unsatisfied = self._solution.unsatisfied
        if not unsatisfied:
            return

        # Prefer packages with as few remaining versions as possible,
        # so that if a conflict is necessary it's forced quickly.
        def _get_min(dependency):
            if dependency.name in self._use_latest:
                # If we're forced to use the latest version of a package, it effectively
                # only has one version to choose from.
                return 1

            locked = self._get_locked(dependency)
            if locked and (
                dependency.constraint.allows(locked.version)
                or locked.is_prerelease()
                and dependency.constraint.allows(locked.version.next_patch)
            ):
                return 1

            # VCS, URL, File or Directory dependencies
            # represent a single version
            if (
                dependency.is_vcs()
                or dependency.is_url()
                or dependency.is_file()
                or dependency.is_directory()
            ):
                return 1

            try:
                return len(self._provider.search_for(dependency))
            except ValueError:
                return 0

        if len(unsatisfied) == 1:
            dependency = unsatisfied[0]
        else:
            dependency = min(*unsatisfied, key=_get_min)

        locked = self._get_locked(dependency)
        if locked is None or not dependency.constraint.allows(locked.version):
            try:
                packages = self._provider.search_for(dependency)
            except ValueError as e:
                self._add_incompatibility(
                    Incompatibility([Term(dependency, True)], PackageNotFoundCause(e))
                )
                return dependency.complete_name

            try:
                version = packages[0]
            except IndexError:
                version = None

            if version is None:
                # If there are no versions that satisfy the constraint,
                # add an incompatibility that indicates that.
                self._add_incompatibility(
                    Incompatibility([Term(dependency, True)], NoVersionsCause())
                )

                return dependency.complete_name
        else:
            version = locked

        version = self._provider.complete_package(version)

        conflict = False
        for incompatibility in self._provider.incompatibilities_for(version):
            self._add_incompatibility(incompatibility)

            # If an incompatibility is already satisfied, then selecting version
            # would cause a conflict.
            #
            # We'll continue adding its dependencies, then go back to
            # unit propagation which will guide us to choose a better version.
            conflict = conflict or all(
                [
                    term.dependency.complete_name == dependency.complete_name
                    or self._solution.satisfies(term)
                    for term in incompatibility.terms
                ]
            )

        if not conflict:
            self._solution.decide(version)
            self._log(
                "selecting {} ({})".format(
                    version.complete_name, version.full_pretty_version
                )
            )

        return dependency.complete_name

    def _excludes_single_version(self, constraint):  # type: (Any) -> bool
        return isinstance(VersionRange().difference(constraint), Version)

    def _result(self):  # type: () -> SolverResult
        """
        Creates a #SolverResult from the decisions in _solution
        """
        decisions = self._solution.decisions

        return SolverResult(
            self._root,
            [p for p in decisions if not p.is_root()],
            self._solution.attempted_solutions,
        )

    def _add_incompatibility(self, incompatibility):  # type: (Incompatibility) -> None
        self._log("fact: {}".format(incompatibility))

        for term in incompatibility.terms:
            if term.dependency.complete_name not in self._incompatibilities:
                self._incompatibilities[term.dependency.complete_name] = []

            if (
                incompatibility
                in self._incompatibilities[term.dependency.complete_name]
            ):
                continue

            self._incompatibilities[term.dependency.complete_name].append(
                incompatibility
            )

    def _get_locked(self, dependency):  # type: (Dependency) -> Union[Package, None]
        if dependency.name in self._use_latest:
            return

        locked = self._locked.get(dependency.name)
        if not locked:
            return

        if not dependency.is_same_package_as(locked):
            return

        return locked

    def _log(self, text):
        self._provider.debug(text, self._solution.attempted_solutions)
