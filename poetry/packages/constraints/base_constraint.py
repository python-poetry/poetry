class BaseConstraint(object):
    def allows_all(self, other):
        raise NotImplementedError()

    def allows_any(self, other):
        raise NotImplementedError()

    def difference(self, other):
        raise NotImplementedError()

    def intersect(self, other):
        raise NotImplementedError()

    def union(self, other):
        raise NotImplementedError()

    def is_any(self):
        return False

    def is_empty(self):
        return False

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, str(self))

    def __eq__(self, other):
        raise NotImplementedError()
