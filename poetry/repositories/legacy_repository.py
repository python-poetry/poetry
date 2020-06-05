import cgi
import re
import warnings

from collections import defaultdict
from typing import Generator
from typing import Optional
from typing import Union

import requests

from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache
from cachy import CacheManager

import poetry.packages

from poetry.locations import CACHE_DIR
from poetry.packages import Package
from poetry.packages import dependency_from_pep_508
from poetry.packages.utils.link import Link
from poetry.semver import Version
from poetry.semver import VersionConstraint
from poetry.semver import VersionRange
from poetry.semver import parse_constraint
from poetry.utils._compat import Path
from poetry.utils.helpers import canonicalize_name
from poetry.utils.inspector import Inspector
from poetry.utils.patterns import wheel_file_re
from poetry.version.markers import InvalidMarker

from .auth import Auth
from .exceptions import PackageNotFound
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

    _links = set()
    _versions_loaded = False

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
                else:
                    self._links.add(link)

                yield link

    def add_link( self, version_url, content, headers ):
        encoding = None
        parsed = None

        if headers and "Content-Type" in headers:
            content_type, params = cgi.parse_header(headers["Content-Type"])

            if "charset" in params:
                encoding = params["charset"]

        if encoding is None:
            parsed = html5lib.parse(content, namespaceHTMLElements=False)
        else:
            parsed = html5lib.parse(
                content, transport_encoding=encoding, namespaceHTMLElements=False
            )

        # Create a LINK based on the parsed content
        for anchor in parsed.findall(".//a"):
            if anchor.get("href"):
                href = anchor.get("href")

                link_url = None

                if version_url.endswith('/') :
                    link_url = version_url + href
                else:
                    link_url = version_url + '/' + href

                pyrequire = anchor.get("data-requires-python")
                pyrequire = unescape(pyrequire) if pyrequire else None

                link = Link(link_url, self, requires_python=pyrequire)


                if link.ext not in self.SUPPORTED_FORMATS:
                    #print( f'Unsupported Link EXT = {link.ext} ' )
                    continue
                else:
                    self._links.add( link )


    def count_versions(self):
       count = 0
       for v in self.versions:
           count += 1

       return count

    def _count_link_urls(self):
       count = 0
       for u in self.get_link_urls():
           count += 1

       return count

    def get_link_urls(self):
        for anchor in self._parsed.findall(".//a"):
            if anchor.get("href"):
                href = anchor.get("href")
                linkurl = self.clean_link(urlparse.urljoin(self._url, href))

                # The _url points to repo_url + package_name
                # Any url longer than that would be version urls
                if self._url >= linkurl :
                    continue
                else:
                    yield linkurl

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
        self, name, url, auth=None, disable_cache=False, cert=None, client_cert=None
    ):  # type: (str, str, Optional[Auth], bool, Optional[Path], Optional[Path]) -> None
        if name == "pypi":
            raise ValueError("The name [pypi] is reserved for repositories")

        self._packages = []
        self._name = name
        self._url = url.rstrip("/")
        self._auth = auth
        self._client_cert = client_cert
        self._cert = cert
        self._inspector = Inspector()
        self._cache_dir = Path(CACHE_DIR) / "cache" / "repositories" / name
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

        self._session = CacheControl(
            requests.session(), cache=FileCache(str(self._cache_dir / "_http"))
        )

        url_parts = urlparse.urlparse(self._url)
        if not url_parts.username and self._auth:
            self._session.auth = self._auth

        if self._cert:
            self._session.verify = str(self._cert)

        if self._client_cert:
            self._session.cert = str(self._client_cert)

        self._disable_cache = disable_cache

    @property
    def cert(self):  # type: () -> Optional[Path]
        return self._cert

    @property
    def client_cert(self):  # type: () -> Optional[Path]
        return self._client_cert

    @property
    def authenticated_url(self):  # type: () -> str
        if not self._auth:
            return self.url

        parsed = urlparse.urlparse(self.url)

        return "{scheme}://{username}:{password}@{netloc}{path}".format(
            scheme=parsed.scheme,
            username=quote(self._auth.auth.username, safe=""),
            password=quote(self._auth.auth.password, safe=""),
            netloc=parsed.netloc,
            path=parsed.path,
        )

    def find_packages(
        self, name, constraint=None, extras=None, allow_prereleases=False
    ):
        packages = []

        if constraint is None:
            constraint = "*"

        if not isinstance(constraint, VersionConstraint):
            constraint = parse_constraint(constraint)

        if isinstance(constraint, VersionRange):
            if (
                constraint.max is not None
                and constraint.max.is_prerelease()
                or constraint.min is not None
                and constraint.min.is_prerelease()
            ):
                allow_prereleases = True

        key = name
        if not constraint.is_any():
            key = "{}:{}".format(key, str(constraint))

        if self._cache.store("matches").has(key):
            versions = self._cache.store("matches").get(key)
        else:
            page = self._get("/{}/".format(canonicalize_name(name).replace(".", "-")))
            if page is None:
                return []

            versions = []
            for version in page.versions:
                if version.is_prerelease() and not allow_prereleases:
                    continue

                if constraint.allows(version):
                    versions.append(version)

            self._cache.store("matches").put(key, versions, 5)

        for version in versions:
            package = Package(name, version)
            package.source_type = "legacy"
            package.source_reference = self.name
            package.source_url = self._url

            if extras is not None:
                package.requires_extras = extras

            packages.append(package)

        self._log(
            "{} packages found for {} {}".format(len(packages), name, str(constraint)),
            level="debug",
        )

        return packages

    def package(
        self, name, version, extras=None
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
            if release_info["requires_python"]:
                package.python_versions = release_info["requires_python"]

            package.source_type = "legacy"
            package.source_url = self._url
            package.source_reference = self.name

            requires_dist = release_info["requires_dist"] or []
            for req in requires_dist:
                try:
                    dependency = dependency_from_pep_508(req)
                except InvalidMarker:
                    # Invalid marker
                    # We strip the markers hoping for the best
                    req = req.split(";")[0]

                    dependency = dependency_from_pep_508(req)
                except ValueError:
                    # Likely unable to parse constraint so we skip it
                    self._log(
                        "Invalid constraint ({}) found in {}-{} dependencies, "
                        "skipping".format(req, package.name, package.version),
                        level="debug",
                    )
                    continue

                if dependency.in_extras:
                    for extra in dependency.in_extras:
                        if extra not in package.extras:
                            package.extras[extra] = []

                        package.extras[extra].append(dependency)

                if not dependency.is_optional():
                    package.requires.append(dependency)

            # Adding description
            package.description = release_info.get("summary", "")

            # Adding hashes information
            package.files = release_info["files"]

            # Activate extra dependencies
            for extra in extras:
                if extra in package.extras:
                    for dep in package.extras[extra]:
                        dep.activate()

                    package.requires += package.extras[extra]

            self._packages.append(package)

            return package

    def _get_release_info(self, name, version):  # type: (str, str) -> dict
        page = self._get("/{}/".format(canonicalize_name(name).replace(".", "-")))
        if page is None:
            raise PackageNotFound('No package named "{}"'.format(name))

        data = {
            "name": name,
            "version": version,
            "summary": "",
            "requires_dist": [],
            "requires_python": None,
            "files": [],
            "_cache_version": str(self.CACHE_VERSION),
        }

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

        data["files"] = files

        info = self._get_info_from_urls(urls)

        data["summary"] = info["summary"]
        data["requires_dist"] = info["requires_dist"]
        data["requires_python"] = info["requires_python"]

        return data

    def _download(self, url, dest):  # type: (str, str) -> None
        r = self._session.get(url, stream=True)
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

    def _get(self, endpoint):  # type: (str) -> Union[Page, None]
        url = self._url + endpoint
        response = self._session.get(url)
        if response.status_code == 404:
            return

        page = Page(url, response.content, response.headers)

        # Check whether the versions are loaded in the page.
        if page.count_versions() == 0 and page.count_link_urls() > 0 :

            # The legacy repositories have versions found in child pages
            # PYPI Repository:
            # https://pypi.org/simple/flask/ : this page contains href elements that point to .whl, tar.gz etc
            #
            # PyPI href elements will be similar to the following href example
            # <a href="https://files.pythonhosted.org/packages/d8/94/7350820/Flask-1.0.4-py2.py3-none-any.whl#sha256=1a21ccc"
            #       data-requires-python="&gt;=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*">Flask-1.0.4-py2.py3-none-any.whl</a>

            #
            # Legacy Repository
            #
            # https://artifactory.repo.com/artifactory/my-repo/py-pkg/ only points to child pages
            # Versions are provided by following pages
            #
            # https://artifactory.repo.com/artifactory/my-repo/py-pkg/0.1.0
            # https://artifactory.repo.com/artifactory/my-repo/py-pkg/0.2.0
            #
            # For legacy repositories, child pages must be read

            # load the content of the child pages
            # and add it the main package page as versions
            for version_url in page.get_link_urls():

                v_res = self._session.get( version_url )
                if v_res.status_code == 404:
                   continue;

                page.add_link( version_url, v_res.content, v_res.headers )

        # mark the page as "loaded" once the versions are added
        if len( page._links ) > 0:
            page._versions_loaded = True

        return page
