# -*- coding: utf-8 -*-
from typing import Union

from poetry.packages import Dependency

from .set_relation import SetRelation


class Term(object):
    """
    A statement about a package which is true or false for a given selection of
    package versions.

    See https://github.com/dart-lang/pub/tree/master/doc/solver.md#term.
    """

    def __init__(self, dependency, is_positive):  # type: (Dependency, bool)  -> None
        self._dependency = dependency
        self._positive = is_positive

    @property
    def inverse(self):  # type: () -> Term
        return Term(self._dependency, not self.is_positive())

    @property
    def dependency(self):
        return self._dependency

    @property
    def constraint(self):
        return self._dependency.constraint

    def is_positive(self):  # type: () -> bool
        return self._positive

    def satisfies(self, other):  # type: (Term) -> bool
        """
        Returns whether this term satisfies another.
        """
        return (
            self.dependency.name == other.dependency.name
            and self.relation(other) == SetRelation.SUBSET
        )

    def relation(self, other):  # type: (Term) -> int
        """
        Returns the relationship between the package versions
        allowed by this term and another.
        """
        if self.dependency.name != other.dependency.name:
            raise ValueError(
                "{} should refer to {}".format(other, self.dependency.name)
            )

        other_constraint = other.constraint

        if other.is_positive():
            if self.is_positive():
                if not self._compatible_dependency(other.dependency):
                    return SetRelation.DISJOINT

                # foo ^1.5.0 is a subset of foo ^1.0.0
                if other_constraint.allows_all(self.constraint):
                    return SetRelation.SUBSET

                # foo ^2.0.0 is disjoint with foo ^1.0.0
                if not self.constraint.allows_any(other_constraint):
                    return SetRelation.DISJOINT

                return SetRelation.OVERLAPPING
            else:
                if not self._compatible_dependency(other.dependency):
                    return SetRelation.OVERLAPPING

                # not foo ^1.0.0 is disjoint with foo ^1.5.0
                if self.constraint.allows_all(other_constraint):
                    return SetRelation.DISJOINT

                # not foo ^1.5.0 overlaps foo ^1.0.0
                # not foo ^2.0.0 is a superset of foo ^1.5.0
                return SetRelation.OVERLAPPING
        else:
            if self.is_positive():
                if not self._compatible_dependency(other.dependency):
                    return SetRelation.SUBSET

                # foo ^2.0.0 is a subset of not foo ^1.0.0
                if not other_constraint.allows_any(self.constraint):
                    return SetRelation.SUBSET

                # foo ^1.5.0 is disjoint with not foo ^1.0.0
                if other_constraint.allows_all(self.constraint):
                    return SetRelation.DISJOINT

                # foo ^1.0.0 overlaps not foo ^1.5.0
                return SetRelation.OVERLAPPING
            else:
                if not self._compatible_dependency(other.dependency):
                    return SetRelation.OVERLAPPING

                # not foo ^1.0.0 is a subset of not foo ^1.5.0
                if self.constraint.allows_all(other_constraint):
                    return SetRelation.SUBSET

                # not foo ^2.0.0 overlaps not foo ^1.0.0
                # not foo ^1.5.0 is a superset of not foo ^1.0.0
                return SetRelation.OVERLAPPING

    def intersect(self, other):  # type: (Term) -> Union[Term, None]
        """
        Returns a Term that represents the packages
        allowed by both this term and another
        """
        if self.dependency.name != other.dependency.name:
            raise ValueError(
                "{} should refer to {}".format(other, self.dependency.name)
            )

        if self._compatible_dependency(other.dependency):
            if self.is_positive() != other.is_positive():
                # foo ^1.0.0 ∩ not foo ^1.5.0 → foo >=1.0.0 <1.5.0
                positive = self if self.is_positive() else other
                negative = other if self.is_positive() else self

                return self._non_empty_term(
                    positive.constraint.difference(negative.constraint), True
                )
            elif self.is_positive():
                # foo ^1.0.0 ∩ foo >=1.5.0 <3.0.0 → foo ^1.5.0
                return self._non_empty_term(
                    self.constraint.intersect(other.constraint), True
                )
            else:
                # not foo ^1.0.0 ∩ not foo >=1.5.0 <3.0.0 → not foo >=1.0.0 <3.0.0
                return self._non_empty_term(
                    self.constraint.union(other.constraint), False
                )
        elif self.is_positive() != other.is_positive():
            return self if self.is_positive() else other
        else:
            return

    def difference(self, other):  # type: (Term) -> Term
        """
        Returns a Term that represents packages
        allowed by this term and not by the other
        """
        return self.intersect(other.inverse)

    def _compatible_dependency(self, other):
        return (
            self.dependency.is_root
            or other.is_root
            or other.name == self.dependency.name
        )

    def _non_empty_term(self, constraint, is_positive):
        if constraint.is_empty():
            return

        dep = Dependency(self.dependency.name, constraint)
        dep.python_versions = str(self.dependency.python_versions)

        return Term(dep, is_positive)

    def __str__(self):
        return "{}{}".format("not " if not self.is_positive() else "", self._dependency)

    def __repr__(self):
        return "<Term {}>".format(str(self))
