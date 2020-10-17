import cgi
import re
import warnings

from collections import defaultdict
from typing import Generator
from typing import Optional
from typing import Union

import requests
import requests.auth

from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache
from cachy import CacheManager

from poetry.core.packages import Package
from poetry.core.packages.utils.link import Link
from poetry.core.semver import Version
from poetry.core.semver import VersionConstraint
from poetry.core.semver import VersionRange
from poetry.core.semver import parse_constraint
from poetry.locations import REPOSITORY_CACHE_DIR
from poetry.utils._compat import Path
from poetry.utils.helpers import canonicalize_name
from poetry.utils.patterns import wheel_file_re

from ..config.config import Config
from ..inspection.info import PackageInfo
from ..installation.authenticator import Authenticator
from .exceptions import PackageNotFound
from .exceptions import RepositoryError
from .pypi_repository import PyPiRepository


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


try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote


with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import html5lib


class Page:

    VERSION_REGEX = re.compile(r"(?i)([a-z0-9_\-.]+?)-(?=\d)([a-z0-9_.!+-]+)")
    SUPPORTED_FORMATS = [
        ".tar.gz",
        ".whl",
        ".zip",
        ".tar.bz2",
        ".tar.xz",
        ".tar.Z",
        ".tar",
    ]

    def __init__(self, url, content, headers):
        if not url.endswith("/"):
            url += "/"

        self._url = url
        encoding = None
        if headers and "Content-Type" in headers:
            content_type, params = cgi.parse_header(headers["Content-Type"])

            if "charset" in params:
                encoding = params["charset"]

        self._content = content

        if encoding is None:
            self._parsed = html5lib.parse(content, namespaceHTMLElements=False)
        else:
            self._parsed = html5lib.parse(
                content, transport_encoding=encoding, namespaceHTMLElements=False
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
                url = self.clean_link(urlparse.urljoin(self._url, href))
                pyrequire = anchor.get("data-requires-python")
                pyrequire = unescape(pyrequire) if pyrequire else None

                link = Link(url, self, requires_python=pyrequire)

                if link.ext not in self.SUPPORTED_FORMATS:
                    continue

                yield link

    def links_for_version(self, version):  # type: (Version) -> Generator[Link]
        for link in self.links:
            if self.link_version(link) == version:
                yield link

    def link_version(self, link):  # type: (Link) -> Union[Version, None]
        m = wheel_file_re.match(link.filename)
        if m:
            version = m.group("ver")
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

    _clean_re = re.compile(r"[^a-z0-9$&+,/:;=?@.#%_\\|-]", re.I)

    def clean_link(self, url):
        """Makes sure a link is fully encoded.  That is, if a ' ' shows up in
        the link, it will be rewritten to %20 (while not over-quoting
        % or other characters)."""
        return self._clean_re.sub(lambda match: "%%%2x" % ord(match.group(0)), url)


class LegacyRepository(PyPiRepository):
    def __init__(
        self, name, url, config=None, disable_cache=False, cert=None, client_cert=None
    ):  # type: (str, str, Optional[Config], bool, Optional[Path], Optional[Path]) -> None
        if name == "pypi":
            raise ValueError("The name [pypi] is reserved for repositories")

        self._packages = []
        self._name = name
        self._url = url.rstrip("/")
        self._client_cert = client_cert
        self._cert = cert
        self._cache_dir = REPOSITORY_CACHE_DIR / name
        self._cache = CacheManager(
            {
                "default": "releases",
                "serializer": "json",
                "stores": {
                    "releases": {"driver": "file", "path": str(self._cache_dir)},
                    "packages": {"driver": "dict"},
                    "matches": {"driver": "dict"},
                },
            }
        )

        self._authenticator = Authenticator(
            config=config or Config(use_environment=True)
        )
        self._basic_auth = None
        username, password = self._authenticator.get_credentials_for_url(self._url)
        if username is not None and password is not None:
            self._basic_auth = requests.auth.HTTPBasicAuth(username, password)

        self._disable_cache = disable_cache

    @property
    def cert(self):  # type: () -> Optional[Path]
        return self._cert

    @property
    def client_cert(self):  # type: () -> Optional[Path]
        return self._client_cert

    @property
    def session(self):
        session = self._authenticator.session

        if self._basic_auth:
            session.auth = self._basic_auth

        if self._cert:
            session.verify = str(self._cert)

        if self._client_cert:
            session.cert = str(self._client_cert)

        return CacheControl(session, cache=FileCache(str(self._cache_dir / "_http")))

    @property
    def authenticated_url(self):  # type: () -> str
        if not self._basic_auth:
            return self.url

        parsed = urlparse.urlparse(self.url)

        return "{scheme}://{username}:{password}@{netloc}{path}".format(
            scheme=parsed.scheme,
            username=quote(self._basic_auth.username, safe=""),
            password=quote(self._basic_auth.password, safe=""),
            netloc=parsed.netloc,
            path=parsed.path,
        )

    def find_packages(self, dependency):
        packages = []

        constraint = dependency.constraint
        if constraint is None:
            constraint = "*"

        if not isinstance(constraint, VersionConstraint):
            constraint = parse_constraint(constraint)

        allow_prereleases = dependency.allows_prereleases()
        if isinstance(constraint, VersionRange):
            if (
                constraint.max is not None
                and constraint.max.is_prerelease()
                or constraint.min is not None
                and constraint.min.is_prerelease()
            ):
                allow_prereleases = True

        key = dependency.name
        if not constraint.is_any():
            key = "{}:{}".format(key, str(constraint))

        ignored_pre_release_versions = []

        if self._cache.store("matches").has(key):
            versions = self._cache.store("matches").get(key)
        else:
            page = self._get("/{}/".format(dependency.name.replace(".", "-")))
            if page is None:
                return []

            versions = []
            for version in page.versions:
                if version.is_prerelease() and not allow_prereleases:
                    if constraint.is_any():
                        # we need this when all versions of the package are pre-releases
                        ignored_pre_release_versions.append(version)
                    continue

                if constraint.allows(version):
                    versions.append(version)

            self._cache.store("matches").put(key, versions, 5)

        for package_versions in (versions, ignored_pre_release_versions):
            for version in package_versions:
                package = Package(
                    dependency.name,
                    version,
                    source_type="legacy",
                    source_reference=self.name,
                    source_url=self._url,
                )

                packages.append(package)

            self._log(
                "{} packages found for {} {}".format(
                    len(packages), dependency.name, str(constraint)
                ),
                level="debug",
            )

            if packages or not constraint.is_any():
                # we have matching packages, or constraint is not (*)
                break

        return packages

    def package(self, name, version, extras=None):  # type: (...) -> Package
        """
        Retrieve the release information.

        This is a heavy task which takes time.
        We have to download a package to get the dependencies.
        We also need to download every file matching this release
        to get the various hashes.

        Note that this will be cached so the subsequent operations
        should be much faster.
        """
        try:
            index = self._packages.index(Package(name, version, version))

            return self._packages[index]
        except ValueError:
            package = super(LegacyRepository, self).package(name, version, extras)
            package._source_type = "legacy"
            package._source_url = self._url
            package._source_reference = self.name

            return package

    def find_links_for_package(self, package):
        page = self._get("/{}/".format(package.name.replace(".", "-")))
        if page is None:
            return []

        return list(page.links_for_version(package.version))

    def _get_release_info(self, name, version):  # type: (str, str) -> dict
        page = self._get("/{}/".format(canonicalize_name(name).replace(".", "-")))
        if page is None:
            raise PackageNotFound('No package named "{}"'.format(name))

        data = PackageInfo(
            name=name,
            version=version,
            summary="",
            platform=None,
            requires_dist=[],
            requires_python=None,
            files=[],
            cache_version=str(self.CACHE_VERSION),
        )

        links = list(page.links_for_version(Version.parse(version)))
        if not links:
            raise PackageNotFound(
                'No valid distribution links found for package: "{}" version: "{}"'.format(
                    name, version
                )
            )
        urls = defaultdict(list)
        files = []
        for link in links:
            if link.is_wheel:
                urls["bdist_wheel"].append(link.url)
            elif link.filename.endswith(
                (".tar.gz", ".zip", ".bz2", ".xz", ".Z", ".tar")
            ):
                urls["sdist"].append(link.url)

            h = link.hash
            if h:
                h = link.hash_name + ":" + link.hash
                files.append({"file": link.filename, "hash": h})

        data.files = files

        info = self._get_info_from_urls(urls)

        data.summary = info.summary
        data.requires_dist = info.requires_dist
        data.requires_python = info.requires_python

        return data.asdict()

    def _get(self, endpoint):  # type: (str) -> Union[Page, None]
        url = self._url + endpoint
        try:
            response = self.session.get(url)
            if response.status_code == 404:
                return
            response.raise_for_status()
        except requests.HTTPError as e:
            raise RepositoryError(e)

        if response.status_code in (401, 403):
            self._log(
                "Authorization error accessing {url}".format(url=url), level="warn"
            )
            return

        return Page(url, response.content, response.headers)
