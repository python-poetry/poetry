from .base_constraint import BaseConstraint
from .constraint import Constraint
from .empty_constraint import EmptyConstraint
from .multi_constraint import MultiConstraint


class UnionConstraint(BaseConstraint):
    def __init__(self, *constraints):
        self._constraints = constraints

    @property
    def constraints(self):
        return self._constraints

    def allows(self, other):
        for constraint in self._constraints:
            if constraint.allows(other):
                return True

        return False

    def allows_any(self, other):
        if other.is_empty():
            return False

        if other.is_any():
            return True

        if isinstance(other, Constraint):
            constraints = [other]
        else:
            constraints = other.constraints

        for our_constraint in self._constraints:
            for their_constraint in constraints:
                if our_constraint.allows_any(their_constraint):
                    return True

        return False

    def allows_all(self, other):
        if other.is_any():
            return False

        if other.is_empty():
            return True

        if isinstance(other, Constraint):
            constraints = [other]
        else:
            constraints = other.constraints

        our_constraints = iter(self._constraints)
        their_constraints = iter(constraints)
        our_constraint = next(our_constraints, None)
        their_constraint = next(their_constraints, None)

        while our_constraint and their_constraint:
            if our_constraint.allows_all(their_constraint):
                their_constraint = next(their_constraints, None)
            else:
                our_constraint = next(our_constraints, None)

        return their_constraint is None

    def intersect(self, other):
        if other.is_any():
            return self

        if other.is_empty():
            return other

        if isinstance(other, Constraint):
            if self.allows(other):
                return other

            return EmptyConstraint()

        new_constraints = []
        for our_constraint in self._constraints:
            for their_constraint in other.constraints:
                intersection = our_constraint.intersect(their_constraint)

                if not intersection.is_empty() and intersection not in new_constraints:
                    new_constraints.append(intersection)

        if not new_constraints:
            return EmptyConstraint()

        return UnionConstraint(*new_constraints)

    def union(self, other):
        if isinstance(other, Constraint):
            constraints = self._constraints
            if other not in self._constraints:
                constraints += (other,)

            return UnionConstraint(*constraints)

    def __eq__(self, other):
        if not isinstance(other, UnionConstraint):
            return False

        return sorted(
            self._constraints, key=lambda c: (c.operator, c.version)
        ) == sorted(other.constraints, key=lambda c: (c.operator, c.version))

    def __str__(self):
        constraints = []
        for constraint in self._constraints:
            constraints.append(str(constraint))

        return "{}".format(" || ").join(constraints)
