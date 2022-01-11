import cgi
import hashlib
import re
import urllib.parse
import warnings

from collections import defaultdict
from html import unescape
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from urllib.parse import quote

import requests.auth
import requests.exceptions

from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache
from cachy import CacheManager
from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link
from poetry.core.semver.helpers import parse_constraint
from poetry.core.semver.version import Version
from poetry.core.semver.version_constraint import VersionConstraint
from poetry.core.semver.version_range import VersionRange

from poetry.config.config import Config
from poetry.inspection.info import PackageInfo
from poetry.locations import REPOSITORY_CACHE_DIR
from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.exceptions import RepositoryError
from poetry.repositories.pypi_repository import PyPiRepository
from poetry.utils.authenticator import Authenticator
from poetry.utils.helpers import canonicalize_name
from poetry.utils.helpers import download_file
from poetry.utils.helpers import temporary_directory
from poetry.utils.patterns import wheel_file_re


if TYPE_CHECKING:
    from poetry.core.packages.dependency import Dependency

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

    def __init__(self, url: str, content: str, headers: Dict[str, Any]) -> None:
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
    def versions(self) -> Iterator[Version]:
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
    def links(self) -> Iterator[Link]:
        for anchor in self._parsed.findall(".//a"):
            if anchor.get("href"):
                href = anchor.get("href")
                url = self.clean_link(urllib.parse.urljoin(self._url, href))
                pyrequire = anchor.get("data-requires-python")
                pyrequire = unescape(pyrequire) if pyrequire else None

                link = Link(url, self, requires_python=pyrequire)

                if link.ext not in self.SUPPORTED_FORMATS:
                    continue

                yield link

    def links_for_version(self, version: Version) -> Iterator[Link]:
        for link in self.links:
            if self.link_version(link) == version:
                yield link

    def link_version(self, link: Link) -> Optional[Version]:
        m = wheel_file_re.match(link.filename)
        if m:
            version = m.group("ver")
        else:
            info, ext = link.splitext()
            match = self.VERSION_REGEX.match(info)
            if not match:
                return None

            version = match.group(2)

        try:
            version = Version.parse(version)
        except ValueError:
            return None

        return version

    _clean_re = re.compile(r"[^a-z0-9$&+,/:;=?@.#%_\\|-]", re.I)

    def clean_link(self, url: str) -> str:
        """Makes sure a link is fully encoded.  That is, if a ' ' shows up in
        the link, it will be rewritten to %20 (while not over-quoting
        % or other characters)."""
        return self._clean_re.sub(lambda match: f"%{match.group(0):2x}", url)


# TODO: revisit whether the LegacyRepository should inherit from PyPiRepository.
# <https://github.com/python-poetry/poetry/pull/4755#discussion_r748865374>.
class LegacyRepository(PyPiRepository):
    def __init__(
        self,
        name: str,
        url: str,
        config: Optional[Config] = None,
        disable_cache: bool = False,
        cert: Optional[Path] = None,
        client_cert: Optional[Path] = None,
    ) -> None:
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

        self._session = CacheControl(
            self._authenticator.session, cache=FileCache(str(self._cache_dir / "_http"))
        )

        username, password = self._authenticator.get_credentials_for_url(self._url)
        if username is not None and password is not None:
            self._authenticator.session.auth = requests.auth.HTTPBasicAuth(
                username, password
            )

        if self._cert:
            self._authenticator.session.verify = str(self._cert)

        if self._client_cert:
            self._authenticator.session.cert = str(self._client_cert)

        self._disable_cache = disable_cache

    @property
    def cert(self) -> Optional[Path]:
        return self._cert

    @property
    def client_cert(self) -> Optional[Path]:
        return self._client_cert

    @property
    def authenticated_url(self) -> str:
        if not self._session.auth:
            return self.url

        parsed = urllib.parse.urlparse(self.url)
        username = quote(self._session.auth.username, safe="")
        password = quote(self._session.auth.password, safe="")

        return f"{parsed.scheme}://{username}:{password}@{parsed.netloc}{parsed.path}"

    def find_packages(self, dependency: "Dependency") -> List[Package]:
        packages = []

        constraint = dependency.constraint
        if constraint is None:
            constraint = "*"

        if not isinstance(constraint, VersionConstraint):
            constraint = parse_constraint(constraint)

        allow_prereleases = dependency.allows_prereleases()
        if isinstance(constraint, VersionRange) and (
            constraint.max is not None
            and constraint.max.is_unstable()
            or constraint.min is not None
            and constraint.min.is_unstable()
        ):
            allow_prereleases = True

        key = dependency.name
        if not constraint.is_any():
            key = f"{key}:{constraint!s}"

        ignored_pre_release_versions = []

        if self._cache.store("matches").has(key):
            versions = self._cache.store("matches").get(key)
        else:
            page = self._get_page(f"/{dependency.name.replace('.', '-')}/")
            if page is None:
                return []

            versions = []
            for version in page.versions:
                if version.is_unstable() and not allow_prereleases:
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
                f"{len(packages)} packages found for {dependency.name} {constraint!s}",
                level="debug",
            )

            if packages or not constraint.is_any():
                # we have matching packages, or constraint is not (*)
                break

        return packages

    def package(
        self, name: str, version: str, extras: Optional[List[str]] = None
    ) -> Package:
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
            package = super().package(name, version, extras)
            package._source_type = "legacy"
            package._source_url = self._url
            package._source_reference = self.name

            return package

    def find_links_for_package(self, package: Package) -> List[Link]:
        page = self._get_page(f"/{package.name.replace('.', '-')}/")
        if page is None:
            return []

        return list(page.links_for_version(package.version))

    def _get_release_info(self, name: str, version: str) -> dict:
        page = self._get_page(f"/{canonicalize_name(name).replace('.', '-')}/")
        if page is None:
            raise PackageNotFound(f'No package named "{name}"')

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
                f'No valid distribution links found for package: "{name}" version:'
                f' "{version}"'
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

            file_hash = f"{link.hash_name}:{link.hash}" if link.hash else None

            if not link.hash or (
                link.hash_name not in ("sha256", "sha384", "sha512")
                and hasattr(hashlib, link.hash_name)
            ):
                with temporary_directory() as temp_dir:
                    filepath = Path(temp_dir) / link.filename
                    self._download(link.url, str(filepath))

                    known_hash = (
                        getattr(hashlib, link.hash_name)() if link.hash_name else None
                    )
                    required_hash = hashlib.sha256()

                    chunksize = 4096
                    with filepath.open("rb") as f:
                        while True:
                            chunk = f.read(chunksize)
                            if not chunk:
                                break
                            if known_hash:
                                known_hash.update(chunk)
                            required_hash.update(chunk)

                    if not known_hash or known_hash.hexdigest() == link.hash:
                        file_hash = f"{required_hash.name}:{required_hash.hexdigest()}"

            files.append({"file": link.filename, "hash": file_hash})

        data.files = files

        info = self._get_info_from_urls(urls)

        data.summary = info.summary
        data.requires_dist = info.requires_dist
        data.requires_python = info.requires_python

        return data.asdict()

    def _get_page(self, endpoint: str) -> Optional[Page]:
        url = self._url + endpoint
        try:
            response = self.session.get(url)
            if response.status_code in (401, 403):
                self._log(
                    f"Authorization error accessing {url}",
                    level="warning",
                )
                return None
            if response.status_code == 404:
                return None
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise RepositoryError(e)

        if response.url != url:
            self._log(
                f"Response URL {response.url} differs from request URL {url}",
                level="debug",
            )

        return Page(response.url, response.content, response.headers)

    def _download(self, url: str, dest: str) -> None:
        return download_file(url, dest, session=self.session)
