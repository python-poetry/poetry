import re

from typing import List
from typing import Union

from .empty_constraint import EmptyConstraint
from .exceptions import ParseVersionError
from .patterns import COMPLETE_VERSION
from .version_constraint import VersionConstraint
from .version_range import VersionRange
from .version_union import VersionUnion


class Version(VersionRange):
    """
    A parsed semantic version number.
    """

    def __init__(
        self,
        major,  # type: int
        minor=None,  # type: Union[int, None]
        patch=None,  # type: Union[int, None]
        rest=None,  # type: Union[int, None]
        pre=None,  # type: Union[str, None]
        build=None,  # type: Union[str, None]
        text=None,  # type: Union[str, None]
        precision=None,  # type: Union[int, None]
    ):  # type: () -> None
        self._major = int(major)
        self._precision = None
        if precision is None:
            self._precision = 1

        if minor is None:
            minor = 0
        else:
            if self._precision is not None:
                self._precision += 1

        self._minor = int(minor)

        if patch is None:
            patch = 0
        else:
            if self._precision is not None:
                self._precision += 1

        if rest is None:
            rest = 0
        else:
            if self._precision is not None:
                self._precision += 1

        if precision is not None:
            self._precision = precision

        self._patch = int(patch)
        self._rest = int(rest)

        if text is None:
            parts = [str(major)]
            if self._precision >= 2 or minor != 0:
                parts.append(str(minor))

                if self._precision >= 3 or patch != 0:
                    parts.append(str(patch))

                if self._precision >= 4 or rest != 0:
                    parts.append(str(rest))

            text = ".".join(parts)
            if pre:
                text += "-{}".format(pre)

            if build:
                text += "+{}".format(build)

        self._text = text

        pre = self._normalize_prerelease(pre)

        self._prerelease = []
        if pre is not None:
            self._prerelease = self._split_parts(pre)

        build = self._normalize_build(build)

        self._build = []
        if build is not None:
            if build.startswith(("-", "+")):
                build = build[1:]

            self._build = self._split_parts(build)

    @property
    def major(self):  # type: () -> int
        return self._major

    @property
    def minor(self):  # type: () -> int
        return self._minor

    @property
    def patch(self):  # type: () -> int
        return self._patch

    @property
    def rest(self):  # type: () -> int
        return self._rest

    @property
    def prerelease(self):  # type: () -> List[str]
        return self._prerelease

    @property
    def build(self):  # type: () -> List[str]
        return self._build

    @property
    def text(self):
        return self._text

    @property
    def precision(self):  # type: () -> int
        return self._precision

    @property
    def stable(self):
        if not self.is_prerelease():
            return self

        return self.next_patch

    @property
    def next_major(self):  # type: () -> Version
        if self.is_prerelease() and self.minor == 0 and self.patch == 0:
            return Version(self.major, self.minor, self.patch)

        return self._increment_major()

    @property
    def next_minor(self):  # type: () -> Version
        if self.is_prerelease() and self.patch == 0:
            return Version(self.major, self.minor, self.patch)

        return self._increment_minor()

    @property
    def next_patch(self):  # type: () -> Version
        if self.is_prerelease():
            return Version(self.major, self.minor, self.patch)

        return self._increment_patch()

    @property
    def next_breaking(self):  # type: () -> Version
        if self.major == 0:
            if self.minor != 0:
                return self._increment_minor()

            if self._precision == 1:
                return self._increment_major()
            elif self._precision == 2:
                return self._increment_minor()

            return self._increment_patch()

        return self._increment_major()

    @property
    def first_prerelease(self):  # type: () -> Version
        return Version.parse(
            "{}.{}.{}-alpha.0".format(self.major, self.minor, self.patch)
        )

    @property
    def min(self):
        return self

    @property
    def max(self):
        return self

    @property
    def full_max(self):
        return self

    @property
    def include_min(self):
        return True

    @property
    def include_max(self):
        return True

    @classmethod
    def parse(cls, text):  # type: (str) -> Version
        match = COMPLETE_VERSION.match(text)
        if match is None:
            raise ParseVersionError('Unable to parse "{}".'.format(text))

        text = text.rstrip(".")

        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) else None
        patch = int(match.group(3)) if match.group(3) else None
        rest = int(match.group(4)) if match.group(4) else None

        pre = match.group(5)
        build = match.group(6)

        if build:
            build = build.lstrip("+")

        return Version(major, minor, patch, rest, pre, build, text)

    def is_any(self):
        return False

    def is_empty(self):
        return False

    def is_prerelease(self):  # type: () -> bool
        return len(self._prerelease) > 0

    def allows(self, version):  # type: (Version) -> bool
        return self == version

    def allows_all(self, other):  # type: (VersionConstraint) -> bool
        return other.is_empty() or other == self

    def allows_any(self, other):  # type: (VersionConstraint) -> bool
        return other.allows(self)

    def intersect(self, other):  # type: (VersionConstraint) -> VersionConstraint
        if other.allows(self):
            return self

        return EmptyConstraint()

    def union(self, other):  # type: (VersionConstraint) -> VersionConstraint
        from .version_range import VersionRange

        if other.allows(self):
            return other

        if isinstance(other, VersionRange):
            if other.min == self:
                return VersionRange(
                    other.min,
                    other.max,
                    include_min=True,
                    include_max=other.include_max,
                )

            if other.max == self:
                return VersionRange(
                    other.min,
                    other.max,
                    include_min=other.include_min,
                    include_max=True,
                )

        return VersionUnion.of(self, other)

    def difference(self, other):  # type: (VersionConstraint) -> VersionConstraint
        if other.allows(self):
            return EmptyConstraint()

        return self

    def equals_without_prerelease(self, other):  # type: (Version) -> bool
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
        )

    def _increment_major(self):  # type: () -> Version
        return Version(self.major + 1, 0, 0, precision=self._precision)

    def _increment_minor(self):  # type: () -> Version
        return Version(self.major, self.minor + 1, 0, precision=self._precision)

    def _increment_patch(self):  # type: () -> Version
        return Version(
            self.major, self.minor, self.patch + 1, precision=self._precision
        )

    def _normalize_prerelease(self, pre):  # type: (str) -> str
        if not pre:
            return

        m = re.match(r"(?i)^(a|alpha|b|beta|c|pre|rc|dev)[-.]?(\d+)?$", pre)
        if not m:
            return

        modifier = m.group(1)
        number = m.group(2)

        if number is None:
            number = 0

        if modifier == "a":
            modifier = "alpha"
        elif modifier == "b":
            modifier = "beta"
        elif modifier in {"c", "pre"}:
            modifier = "rc"
        elif modifier == "dev":
            modifier = "alpha"

        return "{}.{}".format(modifier, number)

    def _normalize_build(self, build):  # type: (str) -> str
        if not build:
            return

        if build.startswith("post"):
            build = build.lstrip("post")

        if not build:
            return

        return build

    def _split_parts(self, text):  # type: (str) -> List[Union[str, int]]
        parts = text.split(".")

        for i, part in enumerate(parts):
            try:
                parts[i] = int(part)
            except (TypeError, ValueError):
                continue

        return parts

    def __lt__(self, other):
        return self._cmp(other) < 0

    def __le__(self, other):
        return self._cmp(other) <= 0

    def __gt__(self, other):
        return self._cmp(other) > 0

    def __ge__(self, other):
        return self._cmp(other) >= 0

    def _cmp(self, other):
        if not isinstance(other, VersionConstraint):
            return NotImplemented

        if not isinstance(other, Version):
            return -other._cmp(self)

        if self.major != other.major:
            return self._cmp_parts(self.major, other.major)

        if self.minor != other.minor:
            return self._cmp_parts(self.minor, other.minor)

        if self.patch != other.patch:
            return self._cmp_parts(self.patch, other.patch)

        if self.rest != other.rest:
            return self._cmp_parts(self.rest, other.rest)

        # Pre-releases always come before no pre-release string.
        if not self.is_prerelease() and other.is_prerelease():
            return 1

        if not other.is_prerelease() and self.is_prerelease():
            return -1

        comparison = self._cmp_lists(self.prerelease, other.prerelease)
        if comparison != 0:
            return comparison

        # Builds always come after no build string.
        if not self.build and other.build:
            return -1

        if not other.build and self.build:
            return 1

        return self._cmp_lists(self.build, other.build)

    def _cmp_parts(self, a, b):
        if a < b:
            return -1
        elif a > b:
            return 1

        return 0

    def _cmp_lists(self, a, b):  # type: (List, List) -> int
        for i in range(max(len(a), len(b))):
            a_part = None
            if i < len(a):
                a_part = a[i]

            b_part = None
            if i < len(b):
                b_part = b[i]

            if a_part == b_part:
                continue

            # Missing parts come after present ones.
            if a_part is None:
                return -1

            if b_part is None:
                return 1

            if isinstance(a_part, int):
                if isinstance(b_part, int):
                    return self._cmp_parts(a_part, b_part)

                return -1
            else:
                if isinstance(b_part, int):
                    return 1

                return self._cmp_parts(a_part, b_part)

        return 0

    def __eq__(self, other):  # type: (Version) -> bool
        if not isinstance(other, Version):
            return NotImplemented

        return (
            self._major == other.major
            and self._minor == other.minor
            and self._patch == other.patch
            and self._rest == other.rest
            and self._prerelease == other.prerelease
            and self._build == other.build
        )

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return self._text

    def __repr__(self):
        return "<Version {}>".format(str(self))

    def __hash__(self):
        return hash(
            (
                self.major,
                self.minor,
                self.patch,
                ".".join(str(p) for p in self.prerelease),
                ".".join(str(p) for p in self.build),
            )
        )
