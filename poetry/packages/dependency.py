from typing import Optional

import poetry.packages

from poetry.semver import Version
from poetry.semver import VersionConstraint
from poetry.semver import VersionRange
from poetry.semver import VersionUnion
from poetry.semver import parse_constraint
from poetry.utils.helpers import canonicalize_name
from poetry.version.markers import AnyMarker
from poetry.version.markers import parse_marker

from .constraints import parse_constraint as parse_generic_constraint
from .constraints.constraint import Constraint
from .constraints.multi_constraint import MultiConstraint
from .constraints.union_constraint import UnionConstraint
from .utils.utils import convert_markers


class Dependency(object):
    def __init__(
        self,
        name,  # type: str
        constraint,  # type: str
        optional=False,  # type: bool
        category="main",  # type: str
        allows_prereleases=False,  # type: bool
        source_name=None,  # type: Optional[str]
    ):
        self._name = canonicalize_name(name)
        self._pretty_name = name

        try:
            if not isinstance(constraint, VersionConstraint):
                self._constraint = parse_constraint(constraint)
            else:
                self._constraint = constraint
        except ValueError:
            self._constraint = parse_constraint("*")

        self._pretty_constraint = str(constraint)
        self._optional = optional
        self._category = category

        if isinstance(self._constraint, VersionRange) and self._constraint.min:
            allows_prereleases = (
                allows_prereleases or self._constraint.min.is_prerelease()
            )

        self._allows_prereleases = allows_prereleases
        self._source_name = source_name

        self._python_versions = "*"
        self._python_constraint = parse_constraint("*")
        self._transitive_python_versions = None
        self._transitive_python_constraint = None
        self._transitive_marker = None

        self._extras = []
        self._in_extras = []

        self._activated = not self._optional

        self.is_root = False
        self.marker = AnyMarker()

    @property
    def name(self):
        return self._name

    @property
    def constraint(self):
        return self._constraint

    @property
    def pretty_constraint(self):
        return self._pretty_constraint

    @property
    def pretty_name(self):
        return self._pretty_name

    @property
    def category(self):
        return self._category

    @property
    def source_name(self):
        return self._source_name

    @property
    def python_versions(self):
        return self._python_versions

    @python_versions.setter
    def python_versions(self, value):
        self._python_versions = value
        self._python_constraint = parse_constraint(value)
        if not self._python_constraint.is_any():
            self.marker = self.marker.intersect(
                parse_marker(
                    self._create_nested_marker(
                        "python_version", self._python_constraint
                    )
                )
            )

    @property
    def transitive_python_versions(self):
        if self._transitive_python_versions is None:
            return self._python_versions

        return self._transitive_python_versions

    @transitive_python_versions.setter
    def transitive_python_versions(self, value):
        self._transitive_python_versions = value
        self._transitive_python_constraint = parse_constraint(value)

    @property
    def transitive_marker(self):
        if self._transitive_marker is None:
            return self.marker

        return self._transitive_marker

    @transitive_marker.setter
    def transitive_marker(self, value):
        self._transitive_marker = value

    @property
    def python_constraint(self):
        return self._python_constraint

    @property
    def transitive_python_constraint(self):
        if self._transitive_python_constraint is None:
            return self._python_constraint

        return self._transitive_python_constraint

    @property
    def extras(self):  # type: () -> list
        return self._extras

    @property
    def in_extras(self):  # type: () -> list
        return self._in_extras

    @property
    def base_pep_508_name(self):  # type: () -> str
        requirement = self.pretty_name

        if self.extras:
            requirement += "[{}]".format(",".join(self.extras))

        if isinstance(self.constraint, VersionUnion):
            if self.constraint.excludes_single_version():
                requirement += " ({})".format(str(self.constraint))
            else:
                requirement += " ({})".format(self.pretty_constraint)
        elif isinstance(self.constraint, Version):
            requirement += " (=={})".format(self.constraint.text)
        elif not self.constraint.is_any():
            requirement += " ({})".format(str(self.constraint).replace(" ", ""))

        return requirement

    def allows_prereleases(self):
        return self._allows_prereleases

    def is_optional(self):
        return self._optional

    def is_activated(self):
        return self._activated

    def is_vcs(self):
        return False

    def is_file(self):
        return False

    def is_directory(self):
        return False

    def is_url(self):
        return False

    def accepts(self, package):  # type: (poetry.packages.Package) -> bool
        """
        Determines if the given package matches this dependency.
        """
        return (
            self._name == package.name
            and self._constraint.allows(package.version)
            and (not package.is_prerelease() or self.allows_prereleases())
        )

    def to_pep_508(self, with_extras=True):  # type: (bool) -> str
        requirement = self.base_pep_508_name

        markers = []
        has_extras = False
        if not self.marker.is_any():
            marker = self.marker
            if not with_extras:
                marker = marker.without_extras()

            if not marker.is_empty():
                markers.append(str(marker))

            has_extras = "extra" in convert_markers(marker)
        else:
            # Python marker
            if self.python_versions != "*":
                python_constraint = self.python_constraint

                markers.append(
                    self._create_nested_marker("python_version", python_constraint)
                )

        in_extras = " || ".join(self._in_extras)
        if in_extras and with_extras and not has_extras:
            markers.append(
                self._create_nested_marker("extra", parse_generic_constraint(in_extras))
            )

        if markers:
            if self.is_vcs():
                requirement += " "

            if len(markers) > 1:
                markers = ["({})".format(m) for m in markers]
                requirement += "; {}".format(" and ".join(markers))
            else:
                requirement += "; {}".format(markers[0])

        return requirement

    def _create_nested_marker(self, name, constraint):
        if isinstance(constraint, (MultiConstraint, UnionConstraint)):
            parts = []
            for c in constraint.constraints:
                multi = False
                if isinstance(c, (MultiConstraint, UnionConstraint)):
                    multi = True

                parts.append((multi, self._create_nested_marker(name, c)))

            glue = " and "
            if isinstance(constraint, UnionConstraint):
                parts = [
                    "({})".format(part[1]) if part[0] else part[1] for part in parts
                ]
                glue = " or "
            else:
                parts = [part[1] for part in parts]

            marker = glue.join(parts)
        elif isinstance(constraint, Constraint):
            marker = '{} {} "{}"'.format(name, constraint.operator, constraint.version)
        elif isinstance(constraint, VersionUnion):
            parts = []
            for c in constraint.ranges:
                parts.append(self._create_nested_marker(name, c))

            glue = " or "
            parts = ["({})".format(part) for part in parts]

            marker = glue.join(parts)
        elif isinstance(constraint, Version):
            if constraint.precision >= 3 and name == "python_version":
                name = "python_full_version"

            marker = '{} == "{}"'.format(name, constraint.text)
        else:
            if constraint.min is not None:
                min_name = name
                if constraint.min.precision >= 3 and name == "python_version":
                    min_name = "python_full_version"

                    if constraint.max is None:
                        name = min_name

                op = ">="
                if not constraint.include_min:
                    op = ">"

                version = constraint.min.text
                if constraint.max is not None:
                    max_name = name
                    if constraint.max.precision >= 3 and name == "python_version":
                        max_name = "python_full_version"

                    text = '{} {} "{}"'.format(min_name, op, version)

                    op = "<="
                    if not constraint.include_max:
                        op = "<"

                    version = constraint.max

                    text += ' and {} {} "{}"'.format(max_name, op, version)

                    return text
            elif constraint.max is not None:
                if constraint.max.precision >= 3 and name == "python_version":
                    name = "python_full_version"

                op = "<="
                if not constraint.include_max:
                    op = "<"

                version = constraint.max
            else:
                return ""

            marker = '{} {} "{}"'.format(name, op, version)

        return marker

    def activate(self):
        """
        Set the dependency as mandatory.
        """
        self._activated = True

    def deactivate(self):
        """
        Set the dependency as optional.
        """
        if not self._optional:
            self._optional = True

        self._activated = False

    def with_constraint(self, constraint):
        new = Dependency(
            self.pretty_name,
            constraint,
            optional=self.is_optional(),
            category=self.category,
            allows_prereleases=self.allows_prereleases(),
        )

        new.is_root = self.is_root
        new.python_versions = self.python_versions

        for extra in self.extras:
            new.extras.append(extra)

        for in_extra in self.in_extras:
            new.in_extras.append(in_extra)

        return new

    def __eq__(self, other):
        if not isinstance(other, Dependency):
            return NotImplemented

        return self._name == other.name and self._constraint == other.constraint

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self._name, self._pretty_constraint))

    def __str__(self):
        if self.is_root:
            return self._pretty_name

        return "{} ({})".format(self._pretty_name, self._pretty_constraint)

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, str(self))
