from poetry.semver.helpers import parse_stability

from .dependency import Dependency


class Package:

    supported_link_types = {
        'require': {
            'description': 'requires',
            'method': 'requires'
        },
        'provide': {
            'description': 'provides',
            'method': 'provides'
        }
    }

    STABILITY_STABLE = 0
    STABILITY_RC = 5
    STABILITY_BETA = 10
    STABILITY_ALPHA = 15
    STABILITY_DEV = 20

    stabilities = {
        'stable': STABILITY_STABLE,
        'rc': STABILITY_RC,
        'beta': STABILITY_BETA,
        'alpha': STABILITY_ALPHA,
        'dev': STABILITY_DEV,
    }

    def __init__(self, name, version, pretty_version):
        """
        Creates a new in memory package.

        :param name: The package's name
        :type name: str

        :param version: The package's version
        :type version: str

        :param pretty_version: The package's non-normalized version
        :type pretty_version: str
        """
        self._pretty_name = name
        self._name = name.lower()

        self._version = version
        self._pretty_version = pretty_version

        self._stability = parse_stability(version)
        self._dev = self._stability == 'dev'

        self.source_type = ''
        self.source_reference = ''
        self.source_url = ''

        self.requires = []
        self.dev_requires = []

        self.category = 'main'
        self.hashes = []
        self.optional = False
        self.python_versions = '*'
        self.platform = '*'

    @property
    def name(self):
        return self._name

    @property
    def pretty_name(self):
        return self._pretty_name

    @property
    def id(self):
        return self._id

    @property
    def version(self):
        return self._version

    @property
    def pretty_version(self):
        return self._pretty_version

    @property
    def unique_name(self):
        return self.name + '-' + self._version

    @property
    def pretty_string(self):
        return self.pretty_name + ' ' + self.pretty_version
    
    @property
    def full_pretty_version(self):
        if not self._dev and self.source_type not in ['hg', 'git']:
            return self._pretty_version

        # if source reference is a sha1 hash -- truncate
        if len(self.source_reference) == 40:
            return '{} {}'.format(self._pretty_version,
                                  self.source_reference[0:7])

        return '{} {}'.format(self._pretty_version, self.source_reference)

    def is_dev(self):
        return self._dev

    def is_prerelease(self):
        return self._stability != 'stable'

    def add_dependency(self, name, constraint=None, category='main'):
        if constraint is None:
            constraint = '*'

        if isinstance(constraint, dict):
            if 'git' in constraint:
                # VCS dependency
                pass
            else:
                version = constraint['version']
                optional = constraint.get('optional', False)
                dependency = Dependency(name, version, optional=optional, category=category)
        else:
            dependency = Dependency(name, constraint, category=category)

        if category == 'dev':
            self.dev_requires.append(dependency)
        else:
            self.requires.append(dependency)

        return dependency

    def __hash__(self):
        return hash((self._name, self._version))

    def __eq__(self, other):
        if not isinstance(other, Package):
            return NotImplemented

        return self._name == other.name and self._version == other.version

    def __str__(self):
        return self.unique_name

    def __repr__(self):
        return '<Package {}>'.format(self.unique_name)
