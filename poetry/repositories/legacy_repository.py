import cgi
import re

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

try:
    from html import unescape
except ImportError:
    try:
        from html.parser import HTMLParser
    except ImportError:
        from HTMLParser import HTMLParser

    unescape = HTMLParser().unescape

from typing import Generator
from typing import Union

import html5lib
import requests

from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache
from cachy import CacheManager

import poetry.packages

from poetry.locations import CACHE_DIR
from poetry.masonry.publishing.uploader import wheel_file_re
from poetry.packages import Package
from poetry.packages import dependency_from_pep_508
from poetry.packages.utils.link import Link
from poetry.semver import parse_constraint
from poetry.semver import Version
from poetry.semver import VersionConstraint
from poetry.utils._compat import Path
from poetry.utils.helpers import canonicalize_name
from poetry.version.markers import InvalidMarker

from .pypi_repository import PyPiRepository


class Page:

    VERSION_REGEX = re.compile('(?i)([a-z0-9_\-.]+?)-(?=\d)([a-z0-9_.!+-]+)')

    def __init__(self, url, content, headers):
        self._url = url
        encoding = None
        if headers and "Content-Type" in headers:
            content_type, params = cgi.parse_header(headers["Content-Type"])

            if "charset" in params:
                encoding = params['charset']

        self._content = content
        self._parsed = html5lib.parse(
            content,
            transport_encoding=encoding,
            namespaceHTMLElements=False,
        )

    @property
    def versions(self):  # type: () -> Generator[Version]
        seen = set()
        for link in self.links:
            version = self.link_version(link)

            if not version:
                continue

            if version in seen:
                continue

            seen.add(version)

            yield version

    @property
    def links(self):  # type: () -> Generator[Link]
        for anchor in self._parsed.findall(".//a"):
            if anchor.get("href"):
                href = anchor.get("href")
                url = self.clean_link(
                    urlparse.urljoin(self._url, href)
                )
                pyrequire = anchor.get('data-requires-python')
                pyrequire = unescape(pyrequire) if pyrequire else None

                yield Link(url, self, requires_python=pyrequire)

    def links_for_version(self, version):  # type: (Version) -> Generator[Link]
        for link in self.links:
            if self.link_version(link) == version:
                yield link

    def link_version(self, link):  # type: (Link) -> Union[Version, None]
        m = wheel_file_re.match(link.filename)
        if m:
            version = m.group('ver')
        else:
            info, ext = link.splitext()
            match = self.VERSION_REGEX.match(info)
            if not match:
                return

            version = match.group(2)

        try:
            version = Version.parse(version)
        except ValueError:
            return

        return version

    _clean_re = re.compile(r'[^a-z0-9$&+,/:;=?@.#%_\\|-]', re.I)

    def clean_link(self, url):
        """Makes sure a link is fully encoded.  That is, if a ' ' shows up in
        the link, it will be rewritten to %20 (while not over-quoting
        % or other characters)."""
        return self._clean_re.sub(
            lambda match: '%%%2x' % ord(match.group(0)), url)


class LegacyRepository(PyPiRepository):

    def __init__(self, name, url):
        if name == 'pypi':
            raise ValueError('The name [pypi] is reserved for repositories')

        self._packages = []
        self._name = name
        self._url = url.rstrip('/')
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

        self._session = CacheControl(
            requests.session(),
            cache=FileCache(str(self._cache_dir / '_http'))
        )

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
            page = self._get('/{}'.format(canonicalize_name(name).replace('.', '-')))
            if page is None:
                raise ValueError('No package named "{}"'.format(name))

            versions = []
            for version in page.versions:
                if (
                    not constraint
                    or (constraint and constraint.allows(version))
                ):
                    versions.append(version)

            self._cache.store('matches').put(key, versions, 5)

        for version in versions:
            package = Package(name, version)
            if extras is not None:
                package.requires_extras = extras

            packages.append(package)

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
            requires_dist = release_info['requires_dist'] or []
            for req in requires_dist:
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
        page = self._get('/{}'.format(canonicalize_name(name).replace('.', '-')))
        if page is None:
            raise ValueError('No package named "{}"'.format(name))

        data = {
            'name': name,
            'version': version,
            'summary': '',
            'requires_dist': [],
            'requires_python': [],
            'digests': []
        }

        links = list(page.links_for_version(Version.parse(version)))
        urls = {}
        hashes = []
        default_link = links[0]
        for link in links:
            if link.is_wheel:
                urls['bdist_wheel'] = link.url
            elif link.filename.endswith('.tar.gz'):
                urls['sdist'] = link.url
            elif link.filename.endswith(('.zip', '.bz2')) and 'sdist' not in urls:
                urls['sdist'] = link.url

            hash = link.hash
            if link.hash_name == 'sha256':
                hashes.append(hash)

        data['digests'] = hashes

        if not urls:
            if default_link.is_wheel:
                m = wheel_file_re.match(default_link.filename)
                python = m.group('pyver')
                platform = m.group('plat')
                if python == 'py2.py3' and platform == 'any':
                    urls['bdist_wheel'] = default_link.url
            elif default_link.filename.endswith('.tar.gz'):
                urls['sdist'] = default_link.url
            elif default_link.filename.endswith(('.zip', '.bz2')) and 'sdist' not in urls:
                urls['sdist'] = default_link.url
            else:
                return data

        info = self._get_info_from_urls(urls)

        data['summary'] = info['summary']
        data['requires_dist'] = info['requires_dist']
        data['requires_python'] = info['requires_python']

        return data

    def _get(self, endpoint):  # type: (str) -> Union[Page, None]
        url = self._url + endpoint
        response = self._session.get(url)
        if response.status_code == 404:
            return

        return Page(url, response.content, response.headers)
