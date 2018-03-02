from poetry.semver.version_parser import VersionParser


class Dependency:

    def __init__(self, name, constraint, optional=False, category='main'):
        self._name = name.lower()
        self._pretty_name = name
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
        return self._pretty_name

    @property
    def category(self):
        return self._category

    def accepts_prereleases(self):
        return False

    def is_optional(self):
        return self._optional

    def is_vcs(self):
        return False

    def __eq__(self, other):
        if not isinstance(other, Dependency):
            return NotImplemented

        return self._name == other.name and self._constraint == other.constraint

    def __hash__(self):
        return hash((self._name, self._pretty_constraint))

    def __str__(self):
        return f'{self._pretty_name} ({self._pretty_constraint})'

    def __repr__(self):
        return f'<Dependency {str(self)}>'
