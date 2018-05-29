class VersionConstraint:
    def is_empty(self):  # type: () -> bool
        raise NotImplementedError()

    def is_any(self):  # type: () -> bool
        raise NotImplementedError()

    def allows(self, version):  # type: (Version) -> bool
        raise NotImplementedError()

    def allows_all(self, other):  # type: (VersionConstraint) -> bool
        raise NotImplementedError()

    def allows_any(self, other):  # type: (VersionConstraint) -> bool
        raise NotImplementedError()

    def intersect(self, other):  # type: (VersionConstraint) -> VersionConstraint
        raise NotImplementedError()

    def union(self, other):  # type: (VersionConstraint) -> VersionConstraint
        raise NotImplementedError()

    def difference(self, other):  # type: (VersionConstraint) -> VersionConstraint
        raise NotImplementedError()
