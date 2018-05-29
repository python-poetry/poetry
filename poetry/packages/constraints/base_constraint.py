class BaseConstraint(object):
    def matches(self, provider):
        raise NotImplementedError()

    def allows_all(self, other):
        raise NotImplementedError()

    def allows_any(self, other):
        raise NotImplementedError()

    def difference(self, other):
        raise NotImplementedError()

    def intersect(self, other):
        raise NotImplementedError()

    def is_empty(self):
        return False
