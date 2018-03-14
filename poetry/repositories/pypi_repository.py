from pathlib import Path
from pip.req import InstallRequirement
from typing import List
from typing import Union

from cachy import CacheManager
from requests import get

from poetry.locations import CACHE_DIR
from poetry.packages import Dependency
from poetry.packages import Package
from poetry.semver.constraints import Constraint
from poetry.semver.constraints.base_constraint import BaseConstraint
from poetry.semver.version_parser import VersionParser

from .repository import Repository


class PyPiRepository(Repository):

    def __init__(self, url='https://pypi.org/', disable_cache=False):
        self._url = url
        self._disable_cache = disable_cache
        self._cache = CacheManager({
            'default': 'releases',
            'serializer': 'json',
            'stores': {
                'releases': {
                    'driver': 'file',
                    'path': Path(CACHE_DIR) / 'cache' / 'repositories' / 'pypi'
                },
                'packages': {
                    'driver': 'dict'
                }
            }
        })
        
        super().__init__()

    def find_packages(self,
                      name: str,
                      constraint: Union[Constraint, str, None] = None,
                      extras: Union[list, None] = None
                      ) -> List[Package]:
        """
        Find packages on the remote server.
        """
        packages = []

        if constraint is not None and not isinstance(constraint, BaseConstraint):
            version_parser = VersionParser()
            constraint = version_parser.parse_constraints(constraint)

        info = self.get_package_info(name)

        versions = []

        for version, release in info['releases'].items():
            if (
                not constraint
                or (constraint and constraint.matches(Constraint('=', version)))
            ):
                versions.append(version)

        for version in versions:
            packages.append(
                self.package(name, version, extras=extras)
            )

        return packages

    def package(self,
                name: str,
                version: str,
                extras: Union[list, None] = None) -> Package:
        try:
            index = self._packages.index(Package(name, version, version))

            return self._packages[index]
        except ValueError:
            if extras is None:
                extras = []

            release_info = self.get_release_info(name, version)
            package = Package(name, version, version)
            requires_dist = release_info['requires_dist'] or []
            for req in requires_dist:
                try:
                    req = InstallRequirement.from_line(req)
                except Exception:
                    # Probably an invalid marker
                    # We strip the markers hoping for the best
                    req = req.split(';')[0]

                    req = InstallRequirement.from_line(req)

                name = req.name
                version = str(req.req.specifier)

                dependency = Dependency(
                    name,
                    version
                )

                if req.markers:
                    # Setting extra dependencies and requirements
                    requirements = self._convert_markers(
                        req.markers._markers
                    )

                    if 'python_version' in requirements:
                        ors = []
                        for or_ in requirements['python_version']:
                            ands = []
                            for op, version in or_:
                                ands.append(f'{op}{version}')

                            ors.append(' '.join(ands))

                        dependency.python_versions = ' || '.join(ors)

                    if 'sys_platform' in requirements:
                        ors = []
                        for or_ in requirements['sys_platform']:
                            ands = []
                            for op, platform in or_:
                                if op == '==':
                                    op = ''

                                ands.append(f'{op}{platform}')

                            ors.append(' '.join(ands))

                        dependency.platform = ' || '.join(ors)

                    if 'extra' in requirements:
                        dependency.deactivate()
                        for _extras in requirements['extra']:
                            for _, extra in _extras:
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

    def search(self, query, mode=0):
        results = []

        search = {
            'name': query
        }

        if mode == self.SEARCH_FULLTEXT:
            search['summary'] = query

        client = ServerProxy(self._url)
        hits = client.search(search, 'or')

        for hit in hits:
            results.append({
                'name': hit['name'],
                'description': hit['summary'],
                'version': hit['version']
            })

        return results

    def get_package_info(self, name: str) -> dict:
        """
        Return the package information given its name.

        The information is returned from the cache if it exists
        or retrieved from the remote server.
        """
        if self._disable_cache:
            return self._get_package_info(name)

        return self._cache.store('packages').remember_forever(
            f'{name}',
            lambda: self._get_package_info(name)
        )

    def _get_package_info(self, name: str) -> dict:
        data = self._get(self._url + f'pypi/{name}/json')
        if data is None:
            raise ValueError(f'Package [{name}] not found.')

        return data

    def get_release_info(self, name: str, version: str) -> dict:
        """
        Return the release information given a package name and a version.

        The information is returned from the cache if it exists
        or retrieved from the remote server.
        """
        if self._disable_cache:
            return self._get_release_info(name, version)

        return self._cache.remember_forever(
            f'{name}:{version}',
            lambda: self._get_release_info(name, version)
        )

    def _get_release_info(self, name: str, version: str) -> dict:
        json_data = self._get(self._url + f'pypi/{name}/{version}/json')
        if json_data is None:
            raise ValueError(f'Package [{name}] not found.')

        info = json_data['info']
        data = {
            'name': info['name'],
            'version': info['version'],
            'summary': info['summary'],
            'platform': info['platform'],
            'requires_dist': info['requires_dist'],
            'requires_python': info['requires_python'],
            'digests': []
        }
        for file_info in json_data['releases'][version]:
            data['digests'].append(file_info['digests']['sha256'])

        return data

    def _get(self, url: str) -> Union[dict, None]:
        json_response = get(url)
        if json_response.status_code == 404:
            return None

        json_data = json_response.json()

        return json_data

    def _group_markers(self, markers):
        groups = [[]]

        for marker in markers:
            assert isinstance(marker, (list, tuple, str))

            if isinstance(marker, list):
                groups[-1].append(self._group_markers(marker))
            elif isinstance(marker, tuple):
                lhs, op, rhs = marker

                groups[-1].append((lhs.value, op, rhs.value))
            else:
                assert marker in ["and", "or"]
                if marker == "or":
                    groups.append([])

        return groups

    def _convert_markers(self, markers):
        groups = self._group_markers(markers)[0]

        requirements = {}

        def _group(_groups, or_=False):
            nonlocal requirements

            for group in _groups:
                if isinstance(group, tuple):
                    variable, op, value = group
                    group_name = str(variable)
                    if group_name not in requirements:
                        requirements[group_name] = [[]]
                    elif or_:
                        requirements[group_name].append([])

                    requirements[group_name][-1].append((str(op), str(value)))
                else:
                    _group(group, or_=True)

        _group(groups)

        return requirements
