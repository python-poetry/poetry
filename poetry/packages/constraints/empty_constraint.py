from .base_constraint import BaseConstraint


class EmptyConstraint(BaseConstraint):

    pretty_string = None

    def matches(self, _):
        return True

    def is_empty(self):
        return True

    def allows_all(self, other):
        return True

    def allows_any(self, other):
        return True

    def intersect(self, other):
        return other

    def difference(self, other):
        return

    def __eq__(self, other):
        return other.is_empty()

    def __str__(self):
        return ""
