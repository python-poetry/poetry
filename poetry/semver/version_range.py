from .empty_constraint import EmptyConstraint
from .version_constraint import VersionConstraint
from .version_union import VersionUnion


class VersionRange(VersionConstraint):
    def __init__(
        self,
        min=None,
        max=None,
        include_min=False,
        include_max=False,
        always_include_max_prerelease=False,
    ):
        self._min = min
        self._max = max
        self._include_min = include_min
        self._include_max = include_max

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max

    @property
    def include_min(self):
        return self._include_min

    @property
    def include_max(self):
        return self._include_max

    def is_empty(self):
        return False

    def is_any(self):
        return self._min is None and self._max is None

    def allows(self, other):  # type: (Version) -> bool
        if self._min is not None:
            if other < self._min:
                return False

            if not self._include_min and other == self._min:
                return False

        if self._max is not None:
            if other > self._max:
                return False

            if not self._include_max and other == self._max:
                return False

        return True

    def allows_all(self, other):  # type: (VersionConstraint) -> bool
        from .version import Version

        if other.is_empty():
            return True

        if isinstance(other, Version):
            return self.allows(other)

        if isinstance(other, VersionUnion):
            return all([self.allows_all(constraint) for constraint in other.ranges])

        if isinstance(other, VersionRange):
            return not other.allows_lower(self) and not other.allows_higher(self)

        raise ValueError("Unknown VersionConstraint type {}.".format(other))

    def allows_any(self, other):  # type: (VersionConstraint) -> bool
        from .version import Version

        if other.is_empty():
            return False

        if isinstance(other, Version):
            return self.allows(other)

        if isinstance(other, VersionUnion):
            return any([self.allows_any(constraint) for constraint in other.ranges])

        if isinstance(other, VersionRange):
            return not other.is_strictly_lower(self) and not other.is_strictly_higher(
                self
            )

        raise ValueError("Unknown VersionConstraint type {}.".format(other))

    def intersect(self, other):  # type: (VersionConstraint) -> VersionConstraint
        from .version import Version

        if other.is_empty():
            return other

        if isinstance(other, VersionUnion):
            return other.intersect(self)

        # A range and a Version just yields the version if it's in the range.
        if isinstance(other, Version):
            if self.allows(other):
                return other

            return EmptyConstraint()

        if not isinstance(other, VersionRange):
            raise ValueError("Unknown VersionConstraint type {}.".format(other))

        if self.allows_lower(other):
            if self.is_strictly_lower(other):
                return EmptyConstraint()

            intersect_min = other.min
            intersect_include_min = other.include_min
        else:
            if other.is_strictly_lower(self):
                return EmptyConstraint()

            intersect_min = self._min
            intersect_include_min = self._include_min

        if self.allows_higher(other):
            intersect_max = other.max
            intersect_include_max = other.include_max
        else:
            intersect_max = self._max
            intersect_include_max = self._include_max

        if intersect_min is None and intersect_max is None:
            return VersionRange()

        # If the range is just a single version.
        if intersect_min == intersect_max:
            # Because we already verified that the lower range isn't strictly
            # lower, there must be some overlap.
            assert intersect_include_min and intersect_include_max

            return intersect_min

        # If we got here, there is an actual range.
        return VersionRange(
            intersect_min, intersect_max, intersect_include_min, intersect_include_max
        )

    def union(self, other):  # type: (VersionConstraint) -> VersionConstraint
        from .version import Version

        if isinstance(other, Version):
            if self.allows(other):
                return self

            if other == self.min:
                return VersionRange(
                    self.min, self.max, include_min=True, include_max=self.include_max
                )

            if other == self.max:
                return VersionRange(
                    self.min, self.max, include_min=self.include_min, include_max=True
                )

            return VersionUnion.of(self, other)

        if isinstance(other, VersionRange):
            # If the two ranges don't overlap, we won't be able to create a single
            # VersionRange for both of them.
            edges_touch = (
                self.max == other.min and (self.include_max or other.include_min)
            ) or (self.min == other.max and (self.include_min or other.include_max))

            if not edges_touch and not self.allows_any(other):
                return VersionUnion.of(self, other)

            if self.allows_lower(other):
                union_min = self.min
                union_include_min = self.include_min
            else:
                union_min = other.min
                union_include_min = other.include_min

            if self.allows_higher(other):
                union_max = self.max
                union_include_max = self.include_max
            else:
                union_max = other.max
                union_include_max = other.include_max

            return VersionRange(
                union_min,
                union_max,
                include_min=union_include_min,
                include_max=union_include_max,
            )

        return VersionUnion.of(self, other)

    def difference(self, other):  # type: (VersionConstraint) -> VersionConstraint
        from .version import Version

        if other.is_empty():
            return self

        if isinstance(other, Version):
            if not self.allows(other):
                return self

            if other == self.min:
                if not self.include_min:
                    return self

                return VersionRange(self.min, self.max, False, self.include_max)

            if other == self.max:
                if not self.include_max:
                    return self

                return VersionRange(self.min, self.max, self.include_min, False)

            return VersionUnion.of(
                VersionRange(self.min, other, self.include_min, False),
                VersionRange(other, self.max, False, self.include_max),
            )
        elif isinstance(other, VersionRange):
            if not self.allows_any(other):
                return self

            if not self.allows_lower(other):
                before = None
            elif self.min == other.min:
                before = self.min
            else:
                before = VersionRange(
                    self.min, other.min, self.include_min, not other.include_min
                )

            if not self.allows_higher(other):
                after = None
            elif self.max == other.max:
                after = self.max
            else:
                after = VersionRange(
                    other.max, self.max, not other.include_max, self.include_max
                )

            if before is None and after is None:
                return EmptyConstraint()

            if before is None:
                return after

            if after is None:
                return before

            return VersionUnion.of(before, after)
        elif isinstance(other, VersionUnion):
            ranges = []  # type: List[VersionRange]
            current = self

            for range in other.ranges:
                # Skip any ranges that are strictly lower than [current].
                if range.is_strictly_lower(current):
                    continue

                # If we reach a range strictly higher than [current], no more ranges
                # will be relevant so we can bail early.
                if range.is_strictly_higher(current):
                    break

                difference = current.difference(range)
                if difference.is_empty():
                    return EmptyConstraint()
                elif isinstance(difference, VersionUnion):
                    # If [range] split [current] in half, we only need to continue
                    # checking future ranges against the latter half.
                    ranges.append(difference.ranges[0])
                    current = difference.ranges[-1]
                else:
                    current = difference

            if not ranges:
                return current

            return VersionUnion.of(*(ranges + [current]))

        raise ValueError("Unknown VersionConstraint type {}.".format(other))

    def allows_lower(self, other):  # type: (VersionRange) -> bool
        if self.min is None:
            return other.min is not None

        if other.min is None:
            return False

        if self.min < other.min:
            return True

        if self.min > other.min:
            return False

        return self.include_min and not other.include_min

    def allows_higher(self, other):  # type: (VersionRange) -> bool
        if self.max is None:
            return other.max is not None

        if other.max is None:
            return False

        if self.max < other.max:
            return False

        if self.max > other.max:
            return True

        return self.include_max and not other.include_max

    def is_strictly_lower(self, other):  # type: (VersionRange) -> bool
        if self.max is None or other.min is None:
            return False

        if self.max < other.min:
            return True

        if self.max > other.min:
            return False

        return not self.include_max or not other.include_min

    def is_strictly_higher(self, other):  # type: (VersionRange) -> bool
        return other.is_strictly_lower(self)

    def is_adjacent_to(self, other):  # type: (VersionRange) -> bool
        if self.max != other.min:
            return False

        return (
            self.include_max
            and not other.include_min
            or not self.include_max
            and other.include_min
        )

    def __eq__(self, other):
        if not isinstance(other, VersionRange):
            return False

        return (
            self._min == other.min
            and self._max == other.max
            and self._include_min == other.include_min
            and self._include_max == other.include_max
        )

    def __lt__(self, other):
        return self._cmp(other) < 0

    def __le__(self, other):
        return self._cmp(other) <= 0

    def __gt__(self, other):
        return self._cmp(other) > 0

    def __ge__(self, other):
        return self._cmp(other) >= 0

    def _cmp(self, other):  # type: (VersionRange) -> int
        if self.min is None:
            if other.min is None:
                return self._compare_max(other)

            return -1
        elif other.min is None:
            return 1

        result = self.min._cmp(other.min)
        if result != 0:
            return result

        if self.include_min != other.include_min:
            return -1 if self.include_min else 1

        return self._compare_max(other)

    def _compare_max(self, other):  # type: (VersionRange) -> int
        if self.max is None:
            if other.max is None:
                return 0

            return 1
        elif other.max is None:
            return -1

        result = self.max._cmp(other.max)
        if result != 0:
            return result

        if self.include_max != other.include_max:
            return 1 if self.include_max else -1

        return 0

    def __str__(self):
        text = ""

        if self.min is not None:
            text += ">=" if self.include_min else ">"
            text += self.min.text

        if self.max is not None:
            if self.min is not None:
                text += ","

            text += "{}{}".format("<=" if self.include_max else "<", self.max.text)

        if self.min is None and self.max is None:
            return "*"

        return text

    def __repr__(self):
        return "<VersionRange ({})>".format(str(self))

    def __hash__(self):
        return hash((self.min, self.max, self.include_min, self.include_max))
