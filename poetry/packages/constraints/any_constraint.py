from .base_constraint import BaseConstraint
from .empty_constraint import EmptyConstraint


class AnyConstraint(BaseConstraint):
    def allows(self, other):
        return True

    def allows_all(self, other):
        return True

    def allows_any(self, other):
        return True

    def difference(self, other):
        if other.is_any():
            return EmptyConstraint()

        return other

    def intersect(self, other):
        return other

    def union(self, other):
        return AnyConstraint()

    def is_any(self):
        return True

    def is_empty(self):
        return False

    def __str__(self):
        return "*"

    def __eq__(self, other):
        return other.is_any()
