import poetry.packages

from poetry.semver.constraints import Constraint
from poetry.semver.constraints import EmptyConstraint
from poetry.semver.constraints import MultiConstraint
from poetry.semver.constraints.base_constraint import BaseConstraint
from poetry.semver.version_parser import VersionParser

from .constraints.generic_constraint import GenericConstraint


class Dependency(object):

    def __init__(self,
                 name,                     # type: str
                 constraint,               # type: str
                 optional=False,           # type: bool
                 category='main',          # type: str
                 allows_prereleases=False  # type: bool
                 ):
        self._name = name.lower()
        self._pretty_name = name
        self._parser = VersionParser()

        try:
            if not isinstance(constraint, BaseConstraint):
                self._constraint = self._parser.parse_constraints(constraint)
            else:
                self._constraint = constraint
        except ValueError:
            self._constraint = self._parser.parse_constraints('*')

        self._pretty_constraint = constraint
        self._optional = optional
        self._category = category
        self._allows_prereleases = allows_prereleases

        self._python_versions = '*'
        self._python_constraint = self._parser.parse_constraints('*')
        self._platform = '*'
        self._platform_constraint = EmptyConstraint()

        self._extras = []
        self._in_extras = []

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
        self._python_constraint = self._parser.parse_constraints(value)

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

    def is_vcs(self):
        return False

    def is_file(self):
        return False

    def accepts(self, package):  # type: (poetry.packages.Package) -> bool
        """
        Determines if the given package matches this dependency.
        """
        return (
            self._name == package.name
            and self._constraint.matches(Constraint('=', package.version))
            and (not package.is_prerelease() or self.allows_prereleases())
        )

    def to_pep_508(self, with_extras=True):  # type: (bool) -> str
        requirement = self.pretty_name

        if isinstance(self.constraint, MultiConstraint):
            requirement += ' ({})'.format(','.join(
                [str(c).replace(' ', '') for c in self.constraint.constraints]
            ))
        else:
            requirement += ' ({})'.format(str(self.constraint).replace(' ', ''))

        # Markers
        markers = []

        # Python marker
        if self.python_versions != '*':
            python_constraint = self.python_constraint

            markers.append(
                self._create_nested_marker('python_version', python_constraint)
            )

        in_extras = ' || '.join(self._in_extras)
        if in_extras and with_extras:
            markers.append(
                self._create_nested_marker(
                    'extra', GenericConstraint.parse(in_extras)
                )
            )

        if markers:
            if len(markers) > 1:
                markers = ['({})'.format(m) for m in markers]
                requirement += '; {}'.format(' and '.join(markers))
            else:
                requirement += '; {}'.format(markers[0])

        return requirement

    def _create_nested_marker(self, name, constraint):
        if isinstance(constraint, MultiConstraint):
            parts = []
            for c in constraint.constraints:
                multi = False
                if isinstance(c, MultiConstraint):
                    multi = True

                parts.append((multi, self._create_nested_marker(name, c)))

            glue = ' and '
            if constraint.is_disjunctive():
                parts = [
                    '({})'.format(part[1]) if part[0] else part[1]
                    for part in parts
                ]
                glue = ' or '
            else:
                parts = [part[1] for part in parts]

            marker = glue.join(parts)
        else:
            marker = '{} {} "{}"'.format(
                name, constraint.string_operator, constraint.version
            )

        return marker

    def activate(self):
        """
        Set the dependency as mandatory.
        """
        self._optional = False

    def deactivate(self):
        """
        Set the dependency as optional.
        """
        self._optional = True

    def __eq__(self, other):
        if not isinstance(other, Dependency):
            return NotImplemented

        return self._name == other.name and self._constraint == other.constraint

    def __hash__(self):
        return hash((self._name, self._pretty_constraint))

    def __str__(self):
        return '{} ({})'.format(
            self._pretty_name, self._pretty_constraint
        )

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, str(self))
