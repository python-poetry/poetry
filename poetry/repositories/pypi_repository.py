from typing import List
from typing import Union

try:
    from xmlrpc.client import ServerProxy
except ImportError:
    from xmlrpclib import ServerProxy

from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache
from cachy import CacheManager
from requests import session

from poetry.locations import CACHE_DIR
from poetry.packages import dependency_from_pep_508
from poetry.packages import Package
from poetry.semver.constraints import Constraint
from poetry.semver.constraints.base_constraint import BaseConstraint
from poetry.semver.version_parser import VersionParser
from poetry.utils._compat import Path
from poetry.version.markers import InvalidMarker

from .repository import Repository


class PyPiRepository(Repository):

    def __init__(self,
                 url='https://pypi.org/',
                 disable_cache=False,
                 fallback=False):
        self._url = url
        self._disable_cache = disable_cache
        self._fallback = fallback

        release_cache_dir = Path(CACHE_DIR) / 'cache' / 'repositories' / 'pypi'
        self._cache = CacheManager({
            'default': 'releases',
            'serializer': 'json',
            'stores': {
                'releases': {
                    'driver': 'file',
                    'path': str(release_cache_dir)
                },
                'packages': {
                    'driver': 'dict'
                }
            }
        })

        self._session = CacheControl(
            session(),
            cache=FileCache(str(release_cache_dir / '_http'))
        )
        
        super(PyPiRepository, self).__init__()

    def find_packages(self,
                      name,             # type: str
                      constraint=None,  # type: Union[Constraint, str, None]
                      extras=None       # type: Union[list, None]
                      ):  # type: (...) -> List[Package]
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
            packages.append(self.package(name, version))

        return packages

    def package(self,
                name,        # type: str
                version,     # type: str
                extras=None  # type: (Union[list, None])
                ):  # type: (...) -> Union[Package, None]
        try:
            index = self._packages.index(Package(name, version, version))

            return self._packages[index]
        except ValueError:
            if extras is None:
                extras = []

            release_info = self.get_release_info(name, version)
            if (
                self._fallback
                and release_info['requires_dist'] is None
                and not release_info['requires_python']
            ):
                # No dependencies set (along with other information)
                # This might be due to actually no dependencies
                # or badly set metadata when uploading
                # So, we return None so that the fallback repository
                # can pick up more accurate info
                return

            package = Package(name, version, version)
            requires_dist = release_info['requires_dist'] or []
            for req in requires_dist:
                try:
                    dependency = dependency_from_pep_508(req)
                except InvalidMarker:
                    # Invalid marker
                    # We strip the markers hoping for the best
                    req = req.split(';')[0]

                    dependency = dependency_from_pep_508(req)
                except ValueError:
                    # Likely unable to parse constraint so we skip it
                    continue

                if dependency.extras:
                    for extra in dependency.extras:
                        if extra not in package.extras:
                            package.extras[extra] = []

                        package.extras[extra].append(dependency)

                if not dependency.is_optional():
                    package.requires.append(dependency)

            # Adding description
            package.description = release_info.get('summary', '')

            if release_info['requires_python']:
                package.python_versions = release_info['requires_python']

            if release_info['platform']:
                package.platform = release_info['platform']

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

        client = ServerProxy('https://pypi.python.org/pypi')
        hits = client.search(search, 'or')

        for hit in hits:
            result = Package(hit['name'], hit['version'], hit['version'])
            result.description = hit['summary']
            results.append(result)

        return results

    def get_package_info(self, name):  # type: (str) -> dict
        """
        Return the package information given its name.

        The information is returned from the cache if it exists
        or retrieved from the remote server.
        """
        if self._disable_cache:
            return self._get_package_info(name)

        return self._cache.store('packages').remember_forever(
            name,
            lambda: self._get_package_info(name)
        )

    def _get_package_info(self, name):  # type: (str) -> dict
        data = self._get('pypi/{}/json'.format(name))
        if data is None:
            raise ValueError('Package [{}] not found.'.format(name))

        return data

    def get_release_info(self, name, version):  # type: (str, str) -> dict
        """
        Return the release information given a package name and a version.

        The information is returned from the cache if it exists
        or retrieved from the remote server.
        """
        if self._disable_cache:
            return self._get_release_info(name, version)

        return self._cache.remember_forever(
            '{}:{}'.format(name, version),
            lambda: self._get_release_info(name, version)
        )

    def _get_release_info(self, name, version):  # type: (str, str) -> dict
        json_data = self._get('pypi/{}/{}/json'.format(name, version))
        if json_data is None:
            raise ValueError('Package [{}] not found.'.format(name))

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

        try:
            version_info = json_data['releases'][version]
        except KeyError:
            version_info = []

        for file_info in version_info:
            data['digests'].append(file_info['digests']['sha256'])

        return data

    def _get(self, endpoint):  # type: (str) -> Union[dict, None]
        json_response = self._session.get(self._url + endpoint)
        if json_response.status_code == 404:
            return None

        json_data = json_response.json()

        return json_data
