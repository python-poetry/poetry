import re

from pathlib import Path
from piptools.cache import DependencyCache
from piptools.repositories import PyPIRepository
from piptools.resolver import Resolver
from piptools.scripts.compile import get_pip_command
from pip.req import InstallRequirement
from pip.exceptions import InstallationError

from cachy import CacheManager

import poetry.packages

from poetry.locations import CACHE_DIR
from poetry.semver.constraints import Constraint
from poetry.semver.constraints.base_constraint import BaseConstraint
from poetry.semver.version_parser import VersionParser

from .repository import Repository


class LegacyRepository(Repository):

    def __init__(self, name, url):
        if name == 'pypi':
            raise ValueError('The name [pypi] is reserved for repositories')

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
                    'path': Path(CACHE_DIR) / 'cache' / 'repositories' / name
                },
                'packages': {
                    'driver': 'dict'
                },
                'matches': {
                    'driver': 'dict'
                }
            }
        })

        super().__init__()

    def find_packages(self, name, constraint=None):
        packages = []

        if constraint is not None and not isinstance(constraint,
                                                     BaseConstraint):
            version_parser = VersionParser()
            constraint = version_parser.parse_constraints(constraint)

        key = name
        if constraint:
            key = f'{key}:{str(constraint)}'

        if self._cache.store('matches').has(key):
            versions = self._cache.store('matches').get(key)
        else:
            candidates = [str(c.version) for c in self._repository.find_all_candidates(name)]

            versions = []
            for version in candidates:
                if version in versions:
                    continue

                if (
                    not constraint
                    or (constraint and constraint.matches(Constraint('=', version)))
                ):
                    versions.append(version)

            self._cache.store('matches').put(key, versions, 5)

        for version in versions:
            packages.append(self.package(name, version))

        return packages

    def package(self, name, version) -> 'poetry.packages.Package':
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
            release_info = self.get_release_info(name, version)
            package = poetry.packages.Package(name, version, version)
            for dependency in release_info['requires_dist']:
                m = re.match(
                    '^(?P<name>[^ ;]+)'
                    '(?: \((?P<version>.+)\))?'
                    '(?:;(?P<extra>(.+)))?$',
                    dependency
                )
                package.requires.append(
                    poetry.packages.Dependency(
                        m.group('name'),
                        m.group('version') or '*',
                        optional=m.group('extra') is not None
                    )
                )

            package.source_type = 'legacy'
            package.source_url = self._url

            # Adding hashes information
            package.hashes = release_info['digests']

            self._packages.append(package)

            return package

    def get_release_info(self, name: str, version: str) -> dict:
        """
        Return the release information given a package name and a version.

        The information is returned from the cache if it exists
        or retrieved from the remote server.
        """
        return self._cache.store('releases').remember_forever(
            f'{name}:{version}',
            lambda: self._get_release_info(name, version)
        )

    def _get_release_info(self, name: str, version: str) -> dict:
        ireq = InstallRequirement.from_line(f'{name}=={version}')
        resolver = Resolver(
            [ireq], self._repository,
            cache=DependencyCache(self._cache_dir.as_posix())
        )
        try:
            requirements = list(resolver._iter_dependencies(ireq))
        except InstallationError as e:
            # setup.py egg-info error most likely
            # So we assume no dependencies
            requirements = []

        requires = []
        for dep in requirements:
            constraint = str(dep.req.specifier)
            require = f'{dep.name}'
            if constraint:
                require += f' ({constraint})'

            requires.append(require)

        hashes = resolver.resolve_hashes([ireq])[ireq]
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
