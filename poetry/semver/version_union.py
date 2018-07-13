from .empty_constraint import EmptyConstraint
from .version_constraint import VersionConstraint


class VersionUnion(VersionConstraint):
    """
    A version constraint representing a union of multiple disjoint version
    ranges.

    An instance of this will only be created if the version can't be represented
    as a non-compound value.
    """

    def __init__(self, *ranges):
        self._ranges = list(ranges)

    @property
    def ranges(self):
        return self._ranges

    @classmethod
    def of(cls, *ranges):
        from .version_range import VersionRange

        flattened = []
        for constraint in ranges:
            if constraint.is_empty():
                continue

            if isinstance(constraint, VersionUnion):
                flattened += constraint.ranges
                continue

            flattened.append(constraint)

        if not flattened:
            return EmptyConstraint()

        if any([constraint.is_any() for constraint in flattened]):
            return VersionRange()

        # Only allow Versions and VersionRanges here so we can more easily reason
        # about everything in flattened. _EmptyVersions and VersionUnions are
        # filtered out above.
        for constraint in flattened:
            if isinstance(constraint, VersionRange):
                continue

            raise ValueError("Unknown VersionConstraint type {}.".format(constraint))

        flattened.sort()

        merged = []
        for constraint in flattened:
            # Merge this constraint with the previous one, but only if they touch.
            if not merged or (
                not merged[-1].allows_any(constraint)
                and not merged[-1].is_adjacent_to(constraint)
            ):
                merged.append(constraint)
            else:
                merged[-1] = merged[-1].union(constraint)

        if len(merged) == 1:
            return merged[0]

        return VersionUnion(*merged)

    def is_empty(self):
        return False

    def is_any(self):
        return False

    def allows(self, version):  # type: (Version) -> bool
        return any([constraint.allows(version) for constraint in self._ranges])

    def allows_all(self, other):  # type: (VersionConstraint) -> bool
        our_ranges = iter(self._ranges)
        their_ranges = iter(self._ranges_for(other))

        our_current_range = next(our_ranges, None)
        their_current_range = next(their_ranges, None)

        while our_current_range and their_current_range:
            if our_current_range.allows_all(their_current_range):
                their_current_range = next(their_ranges, None)
            else:
                our_current_range = next(our_ranges, None)

        return their_current_range is None

    def allows_any(self, other):  # type: (VersionConstraint) -> bool
        our_ranges = iter(self._ranges)
        their_ranges = iter(self._ranges_for(other))

        our_current_range = next(our_ranges, None)
        their_current_range = next(their_ranges, None)

        while our_current_range and their_current_range:
            if our_current_range.allows_any(their_current_range):
                return True

            if their_current_range.allows_higher(our_current_range):
                our_current_range = next(our_ranges, None)
            else:
                their_current_range = next(their_ranges, None)

        return False

    def intersect(self, other):  # type: (VersionConstraint) -> VersionConstraint
        our_ranges = iter(self._ranges)
        their_ranges = iter(self._ranges_for(other))
        new_ranges = []

        our_current_range = next(our_ranges, None)
        their_current_range = next(their_ranges, None)

        while our_current_range and their_current_range:
            intersection = our_current_range.intersect(their_current_range)

            if not intersection.is_empty():
                new_ranges.append(intersection)

            if their_current_range.allows_higher(our_current_range):
                our_current_range = next(our_ranges, None)
            else:
                their_current_range = next(their_ranges, None)

        return VersionUnion.of(*new_ranges)

    def union(self, other):  # type: (VersionConstraint) -> VersionConstraint
        return VersionUnion.of(self, other)

    def difference(self, other):  # type: (VersionConstraint) -> VersionConstraint
        our_ranges = iter(self._ranges)
        their_ranges = iter(self._ranges_for(other))
        new_ranges = []

        state = {
            "current": next(our_ranges, None),
            "their_range": next(their_ranges, None),
        }

        def their_next_range():
            state["their_range"] = next(their_ranges, None)
            if state["their_range"]:
                return True

            new_ranges.append(state["current"])
            our_current = next(our_ranges, None)
            while our_current:
                new_ranges.append(our_current)
                our_current = next(our_ranges, None)

            return False

        def our_next_range(include_current=True):
            if include_current:
                new_ranges.append(state["current"])

            our_current = next(our_ranges, None)
            if not our_current:
                return False

            state["current"] = our_current

            return True

        while True:
            if state["their_range"].is_strictly_lower(state["current"]):
                if not their_next_range():
                    break

                continue

            if state["their_range"].is_strictly_higher(state["current"]):
                if not our_next_range():
                    break

                continue

            difference = state["current"].difference(state["their_range"])
            if isinstance(difference, VersionUnion):
                assert len(difference.ranges) == 2
                new_ranges.append(difference.ranges[0])
                state["current"] = difference.ranges[-1]

                if not their_next_range():
                    break
            elif difference.is_empty():
                if not our_next_range(False):
                    break
            else:
                state["current"] = difference

                if state["current"].allows_higher(state["their_range"]):
                    if not their_next_range():
                        break
                else:
                    if not our_next_range():
                        break

        if not new_ranges:
            return EmptyConstraint()

        if len(new_ranges) == 1:
            return new_ranges[0]

        return VersionUnion.of(*new_ranges)

    def _ranges_for(
        self, constraint
    ):  # type: (VersionConstraint) -> List[VersionRange]
        from .version_range import VersionRange

        if constraint.is_empty():
            return []

        if isinstance(constraint, VersionUnion):
            return constraint.ranges

        if isinstance(constraint, VersionRange):
            return [constraint]

        raise ValueError("Unknown VersionConstraint type {}".format(constraint))

    def _excludes_single_version(self):  # type: () -> bool
        from .version import Version
        from .version_range import VersionRange

        return isinstance(VersionRange().difference(self), Version)

    def __eq__(self, other):
        if not isinstance(other, VersionUnion):
            return False

        return self._ranges == other.ranges

    def __str__(self):
        from .version_range import VersionRange

        if self._excludes_single_version():
            return "!={}".format(VersionRange().difference(self))

        return " || ".join([str(r) for r in self._ranges])

    def __repr__(self):
        return "<VersionUnion {}>".format(str(self))
