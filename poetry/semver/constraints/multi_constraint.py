from .base_constraint import BaseConstraint


class MultiConstraint(BaseConstraint):

    def __init__(self, constraints, conjunctive=True):
        self._constraints = tuple(constraints)
        self._conjunctive = conjunctive

    @property
    def constraints(self):
        return self._constraints

    def is_conjunctive(self):
        return self._conjunctive

    def is_disjunctive(self):
        return not self._conjunctive

    def matches(self, provider):
        if self.is_disjunctive():
            for constraint in self._constraints:
                if constraint.matches(provider):
                    return True

            return False

        for constraint in self._constraints:
            if not constraint.matches(provider):
                return False

        return True

    def __str__(self):
        constraints = []
        for constraint in self._constraints:
            constraints.append(str(constraint))

        return '{}'.format(
            (' ' if self._conjunctive else ' || ').join(constraints)
        )
