from .base_constraint import BaseConstraint


class EmptyConstraint(BaseConstraint):

    pretty_string = None

    def matches(self, _):
        return True

    def __str__(self):
        return '*'
