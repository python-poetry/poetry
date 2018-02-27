from poetry.semver.version_parser import VersionParser


class Dependency:

    def __init__(self, name, constraint, optional=False, category='main'):
        self._name = name.lower()
        try:
            self._constraint = VersionParser().parse_constraints(constraint)
        except ValueError:
            self._constraint = VersionParser().parse_constraints('*')

        self._pretty_constraint = constraint
        self._optional = optional
        self._category = category

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
        return '{} ({})'.format(self._name, self._pretty_constraint)

    @property
    def category(self):
        return self._category

    def accepts_prereleases(self):
        return False

    def is_optional(self):
        return self._optional

    def __eq__(self, other):
        if not isinstance(other, Dependency):
            return NotImplemented

        return self._name == other.name and self._constraint == other.constraint

    def __hash__(self):
        return hash((self._name, self._pretty_constraint))

    def __str__(self):
        return self.pretty_name

    def __repr__(self):
        return '<Dependency {}>'.format(self.pretty_name)
