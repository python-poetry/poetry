class EmptyConstraint:

    pretty_string = None

    def matches(self, _):
        return True

    def __str__(self):
        return '[]'
