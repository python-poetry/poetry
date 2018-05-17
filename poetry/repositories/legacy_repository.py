from pip._vendor.pkg_resources import RequirementParseError

try:
    from pip._internal.exceptions import InstallationError
    from pip._internal.req import InstallRequirement
except ImportError:
    from pip.exceptions import InstallationError
    from pip.req import InstallRequirement

from piptools.cache import DependencyCache
from piptools.repositories import PyPIRepository
from piptools.resolver import Resolver
from piptools.scripts.compile import get_pip_command

from cachy import CacheManager

import poetry.packages

from poetry.locations import CACHE_DIR
from poetry.packages import Package
from poetry.packages import dependency_from_pep_508
from poetry.semver import parse_constraint
from poetry.semver import Version
from poetry.semver import VersionConstraint
from poetry.utils._compat import Path
from poetry.version.markers import InvalidMarker

from .pypi_repository import PyPiRepository


class LegacyRepository(PyPiRepository):

    def __init__(self, name, url):
        if name == 'pypi':
            raise ValueError('The name [pypi] is reserved for repositories')

        self._packages = []
        self._name = name
        self._url = url
        command = get_pip_command()
        opts, _ = command.parse_args([])
        self._session = command._build_session(opts)
        self._repository = PyPIRepository(opts, self._session)
        self._cache_dir = Path(CACHE_DIR) / 'cache' / 'repositories' / name

        self._cache = CacheManager({
            'default': 'releases',
            'serializer': 'json',
            'stores': {
                'releases': {
                    'driver': 'file',
                    'path': str(self._cache_dir)
                },
                'packages': {
                    'driver': 'dict'
                },
                'matches': {
                    'driver': 'dict'
                }
            }
        })

    @property
    def name(self):
        return self._name

    def find_packages(self, name, constraint=None,
                      extras=None,
                      allow_prereleases=False):
        packages = []

        if constraint is not None and not isinstance(constraint,
                                                     VersionConstraint):
            constraint = parse_constraint(constraint)

        key = name
        if constraint:
            key = '{}:{}'.format(key, str(constraint))

        if self._cache.store('matches').has(key):
            versions = self._cache.store('matches').get(key)
        else:
            candidates = [str(c.version) for c in self._repository.find_all_candidates(name)]

            versions = []
            for version in candidates:
                if version in versions:
                    continue

                try:
                    version = Version.parse(version)
                except ValueError:
                    continue

                if (
                    not constraint
                    or (constraint and constraint.allows(version))
                ):
                    versions.append(version)

            self._cache.store('matches').put(key, versions, 5)

        for version in versions:
            packages.append(Package(name, version, extras=extras))

        return packages

    def package(self, name, version, extras=None
                ):  # type: (...) -> poetry.packages.Package
        """
        Retrieve the release information.

        This is a heavy task which takes time.
        We have to download a package to get the dependencies.
        We also need to download every file matching this release
        to get the various hashes.
        
        Note that, this will be cached so the subsequent operations
        should be much faster.
        """
        try:
            index = self._packages.index(
                poetry.packages.Package(name, version, version)
            )

            return self._packages[index]
        except ValueError:
            if extras is None:
                extras = []

            release_info = self.get_release_info(name, version)
            package = poetry.packages.Package(name, version, version)
            for req in release_info['requires_dist']:
                try:
                    dependency = dependency_from_pep_508(req)
                except InvalidMarker:
                    # Invalid marker
                    # We strip the markers hoping for the best
                    req = req.split(';')[0]

                    dependency = dependency_from_pep_508(req)

                if dependency.extras:
                    for extra in dependency.extras:
                        if extra not in package.extras:
                            package.extras[extra] = []

                        package.extras[extra].append(dependency)

                if not dependency.is_optional():
                    package.requires.append(dependency)

            # Adding description
            package.description = release_info.get('summary', '')

            # Adding hashes information
            package.hashes = release_info['digests']

            # Activate extra dependencies
            for extra in extras:
                if extra in package.extras:
                    for dep in package.extras[extra]:
                        dep.activate()

                    package.requires += package.extras[extra]

            self._packages.append(package)

            return package

    def get_release_info(self, name, version):  # type: (str, str) -> dict
        """
        Return the release information given a package name and a version.

        The information is returned from the cache if it exists
        or retrieved from the remote server.
        """
        return self._cache.store('releases').remember_forever(
            '{}:{}'.format(name, version),
            lambda: self._get_release_info(name, version)
        )

    def _get_release_info(self, name, version):  # type: (str, str) -> dict
        ireq = InstallRequirement.from_line('{}=={}'.format(name, version))
        resolver = Resolver(
            [ireq], self._repository,
            cache=DependencyCache(self._cache_dir.as_posix())
        )
        try:
            requirements = list(resolver._iter_dependencies(ireq))
        except (InstallationError, RequirementParseError):
            # setup.py egg-info error most likely
            # So we assume no dependencies
            requirements = []

        requires = []
        for dep in requirements:
            constraint = str(dep.req.specifier)
            require = dep.name
            if constraint:
                require += ' ({})'.format(constraint)

            requires.append(require)

        try:
            hashes = resolver.resolve_hashes([ireq])[ireq]
        except IndexError:
            # Sometimes pip-tools fails when getting indices
            hashes = []

        hashes = [h.split(':')[1] for h in hashes]

        data = {
            'name': name,
            'version': version,
            'summary': '',
            'requires_dist': requires,
            'digests': hashes
        }

        resolver.repository.freshen_build_caches()

        return data
