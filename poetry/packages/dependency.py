import poetry.packages

from poetry.semver import parse_constraint
from poetry.semver import Version
from poetry.semver import VersionConstraint
from poetry.semver import VersionRange
from poetry.semver import VersionUnion
from poetry.utils.helpers import canonicalize_name

from .constraints.empty_constraint import EmptyConstraint
from .constraints.generic_constraint import GenericConstraint
from .constraints.multi_constraint import MultiConstraint


class Dependency(object):
    def __init__(
        self,
        name,  # type: str
        constraint,  # type: str
        optional=False,  # type: bool
        category="main",  # type: str
        allows_prereleases=False,  # type: bool
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

        self._python_versions = "*"
        self._python_constraint = parse_constraint("*")
        self._platform = "*"
        self._platform_constraint = EmptyConstraint()

        self._extras = []
        self._in_extras = []

        self._activated = not self._optional

        self.is_root = False

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
    def python_versions(self):
        return self._python_versions

    @python_versions.setter
    def python_versions(self, value):
        self._python_versions = value
        self._python_constraint = parse_constraint(value)

    @property
    def python_constraint(self):
        return self._python_constraint

    @property
    def platform(self):
        return self._platform

    @platform.setter
    def platform(self, value):
        self._platform = value
        self._platform_constraint = GenericConstraint.parse(value)

    @property
    def platform_constraint(self):
        return self._platform_constraint

    @property
    def extras(self):  # type: () -> list
        return self._extras

    @property
    def in_extras(self):  # type: () -> list
        return self._in_extras

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
        requirement = self.pretty_name

        if self.extras:
            requirement += "[{}]".format(",".join(self.extras))

        if isinstance(self.constraint, VersionUnion):
            requirement += " ({})".format(
                ",".join([str(c).replace(" ", "") for c in self.constraint.ranges])
            )
        elif isinstance(self.constraint, Version):
            requirement += " (=={})".format(self.constraint.text)
        elif not self.constraint.is_any():
            requirement += " ({})".format(str(self.constraint).replace(" ", ""))

        # Markers
        markers = []

        # Python marker
        if self.python_versions != "*":
            python_constraint = self.python_constraint

            markers.append(
                self._create_nested_marker("python_version", python_constraint)
            )

        if self.platform != "*":
            platform_constraint = self.platform_constraint

            markers.append(
                self._create_nested_marker("sys_platform", platform_constraint)
            )

        in_extras = " || ".join(self._in_extras)
        if in_extras and with_extras:
            markers.append(
                self._create_nested_marker("extra", GenericConstraint.parse(in_extras))
            )

        if markers:
            if len(markers) > 1:
                markers = ["({})".format(m) for m in markers]
                requirement += "; {}".format(" and ".join(markers))
            else:
                requirement += "; {}".format(markers[0])

        return requirement

    def _create_nested_marker(self, name, constraint):
        if isinstance(constraint, MultiConstraint):
            parts = []
            for c in constraint.constraints:
                multi = False
                if isinstance(c, MultiConstraint):
                    multi = True

                parts.append((multi, self._create_nested_marker(name, c)))

            glue = " and "
            if constraint.is_disjunctive():
                parts = [
                    "({})".format(part[1]) if part[0] else part[1] for part in parts
                ]
                glue = " or "
            else:
                parts = [part[1] for part in parts]

            marker = glue.join(parts)
        elif isinstance(constraint, GenericConstraint):
            marker = '{} {} "{}"'.format(
                name, constraint.string_operator, constraint.version
            )
        elif isinstance(constraint, VersionUnion):
            parts = []
            for c in constraint.ranges:
                parts.append(self._create_nested_marker(name, c))

            glue = " or "
            parts = ["({})".format(part) for part in parts]

            marker = glue.join(parts)
        elif isinstance(constraint, Version):
            marker = '{} == "{}"'.format(name, constraint.text)
        else:
            if constraint.min is not None:
                op = ">="
                if not constraint.include_min:
                    op = ">"

                version = constraint.min.text
                if constraint.max is not None:
                    text = '{} {} "{}"'.format(name, op, version)

                    op = "<="
                    if not constraint.include_max:
                        op = "<"

                    version = constraint.max

                    text += ' and {} {} "{}"'.format(name, op, version)

                    return text
            elif constraint.max is not None:
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
        new.platform = self.platform

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
