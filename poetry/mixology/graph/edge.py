class Edge:
    """
    A directed edge of a DependencyGraph
    """

    def __init__(self, origin, destination, requirement):
        self._origin = origin
        self._destination = destination
        self._requirement = requirement

    @property
    def origin(self):
        return self._origin

    @property
    def destination(self):
        return self._destination

    @property
    def requirement(self):
        return self._requirement

    def __eq__(self, other):
        return self._origin == other.origin and self._destination == other.destination

    def __repr__(self):
        return '<Edge {} -> {}>'.format(
            self._origin.name, self._destination.name
        )

