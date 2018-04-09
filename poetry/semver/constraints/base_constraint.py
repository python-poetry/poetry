class BaseConstraint(object):

    def matches(self, provider):
        raise NotImplementedError()
