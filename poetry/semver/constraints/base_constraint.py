class BaseConstraint:

    def matches(self, provider):
        raise NotImplementedError()
