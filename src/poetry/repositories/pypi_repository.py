from __future__ import annotations

import hashlib
import logging
import os
import urllib.parse

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import requests

from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache
from cachecontrol.controller import logger as cache_control_logger
from cachy import CacheManager
from html5lib.html5parser import parse
from poetry.core.packages.dependency import Dependency
from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link
from poetry.core.semver.helpers import parse_constraint
from poetry.core.semver.version_constraint import VersionConstraint
from poetry.core.semver.version_range import VersionRange
from poetry.core.version.exceptions import InvalidVersion
from poetry.core.version.markers import parse_marker

from poetry.locations import REPOSITORY_CACHE_DIR
from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.remote_repository import RemoteRepository
from poetry.utils._compat import to_str
from poetry.utils.helpers import download_file
from poetry.utils.helpers import temporary_directory
from poetry.utils.patterns import wheel_file_re


cache_control_logger.setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from poetry.inspection.info import PackageInfo


class PyPiRepository(RemoteRepository):

    CACHE_VERSION = parse_constraint("1.0.0")

    def __init__(
        self,
        url: str = "https://pypi.org/",
        disable_cache: bool = False,
        fallback: bool = True,
    ) -> None:
        super().__init__(url.rstrip("/") + "/simple/")

        self._base_url = url
        self._disable_cache = disable_cache
        self._fallback = fallback

        release_cache_dir = REPOSITORY_CACHE_DIR / "pypi"
        self._cache = CacheManager(
            {
                "default": "releases",
                "serializer": "json",
                "stores": {
                    "releases": {"driver": "file", "path": str(release_cache_dir)},
                    "packages": {"driver": "dict"},
                },
            }
        )

        self._cache_control_cache = FileCache(str(release_cache_dir / "_http"))
        self._session = CacheControl(
            requests.session(), cache=self._cache_control_cache
        )

        self._name = "PyPI"

    @property
    def session(self) -> CacheControl:
        return self._session

    def __del__(self) -> None:
        self._session.close()

    def find_packages(self, dependency: Dependency) -> list[Package]:
        """
        Find packages on the remote server.
        """
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

        try:
            info = self.get_package_info(dependency.name)
        except PackageNotFound:
            self._log(
                f"No packages found for {dependency.name} {constraint!s}",
                level="debug",
            )
            return []

        packages = []
        ignored_pre_release_packages = []

        for version, release in info["releases"].items():
            if not release:
                # Bad release
                self._log(
                    f"No release information found for {dependency.name}-{version},"
                    " skipping",
                    level="debug",
                )
                continue

            try:
                package = Package(info["info"]["name"], version)
            except InvalidVersion:
                self._log(
                    f'Unable to parse version "{version}" for the'
                    f" {dependency.name} package, skipping",
                    level="debug",
                )
                continue

            if package.is_prerelease() and not allow_prereleases:
                if constraint.is_any():
                    # we need this when all versions of the package are pre-releases
                    ignored_pre_release_packages.append(package)
                continue

            if not constraint or (constraint and constraint.allows(package.version)):
                packages.append(package)

        self._log(
            f"{len(packages)} packages found for {dependency.name} {constraint!s}",
            level="debug",
        )

        return packages or ignored_pre_release_packages

    def package(
        self,
        name: str,
        version: str,
        extras: (list | None) = None,
    ) -> Package:
        return self.get_release_info(name, version).to_package(name=name, extras=extras)

    def search(self, query: str) -> list[Package]:
        results = []

        search = {"q": query}

        response = requests.session().get(self._base_url + "search", params=search)
        content = parse(response.content, namespaceHTMLElements=False)
        for result in content.findall(".//*[@class='package-snippet']"):
            name = result.find("h3/*[@class='package-snippet__name']").text
            version = result.find("h3/*[@class='package-snippet__version']").text

            if not name or not version:
                continue

            description = result.find("p[@class='package-snippet__description']").text
            if not description:
                description = ""

            try:
                result = Package(name, version, description)
                result.description = to_str(description.strip())
                results.append(result)
            except InvalidVersion:
                self._log(
                    f'Unable to parse version "{version}" for the {name} package,'
                    " skipping",
                    level="debug",
                )

        return results

    def get_package_info(self, name: str) -> dict:
        """
        Return the package information given its name.

        The information is returned from the cache if it exists
        or retrieved from the remote server.
        """
        if self._disable_cache:
            return self._get_package_info(name)

        return self._cache.store("packages").remember_forever(
            name, lambda: self._get_package_info(name)
        )

    def _get_package_info(self, name: str) -> dict:
        data = self._get(f"pypi/{name}/json")
        if data is None:
            raise PackageNotFound(f"Package [{name}] not found.")

        return data

    def get_release_info(self, name: str, version: str) -> PackageInfo:
        """
        Return the release information given a package name and a version.

        The information is returned from the cache if it exists
        or retrieved from the remote server.
        """
        from poetry.inspection.info import PackageInfo

        if self._disable_cache:
            return PackageInfo.load(self._get_release_info(name, version))

        cached = self._cache.remember_forever(
            f"{name}:{version}", lambda: self._get_release_info(name, version)
        )

        cache_version = cached.get("_cache_version", "0.0.0")
        if parse_constraint(cache_version) != self.CACHE_VERSION:
            # The cache must be updated
            self._log(
                f"The cache for {name} {version} is outdated. Refreshing.",
                level="debug",
            )
            cached = self._get_release_info(name, version)

            self._cache.forever(f"{name}:{version}", cached)

        return PackageInfo.load(cached)

    def find_links_for_package(self, package: Package) -> list[Link]:
        json_data = self._get(f"pypi/{package.name}/{package.version}/json")
        if json_data is None:
            return []

        links = []
        for url in json_data["urls"]:
            h = f"sha256={url['digests']['sha256']}"
            links.append(Link(url["url"] + "#" + h))

        return links

    def _get_release_info(self, name: str, version: str) -> dict:
        from poetry.inspection.info import PackageInfo

        self._log(f"Getting info for {name} ({version}) from PyPI", "debug")

        json_data = self._get(f"pypi/{name}/{version}/json")
        if json_data is None:
            raise PackageNotFound(f"Package [{name}] not found.")

        info = json_data["info"]

        data = PackageInfo(
            name=info["name"],
            version=info["version"],
            summary=info["summary"],
            platform=info["platform"],
            requires_dist=info["requires_dist"],
            requires_python=info["requires_python"],
            files=info.get("files", []),
            cache_version=str(self.CACHE_VERSION),
        )

        try:
            version_info = json_data["releases"][version]
        except KeyError:
            version_info = []

        for file_info in version_info:
            data.files.append(
                {
                    "file": file_info["filename"],
                    "hash": "sha256:" + file_info["digests"]["sha256"],
                }
            )

        if self._fallback and data.requires_dist is None:
            self._log("No dependencies found, downloading archives", level="debug")
            # No dependencies set (along with other information)
            # This might be due to actually no dependencies
            # or badly set metadata when uploading
            # So, we need to make sure there is actually no
            # dependencies by introspecting packages
            urls = defaultdict(list)
            for url in json_data["urls"]:
                # Only get sdist and wheels if they exist
                dist_type = url["packagetype"]
                if dist_type not in ["sdist", "bdist_wheel"]:
                    continue

                urls[dist_type].append(url["url"])

            if not urls:
                return data.asdict()

            info = self._get_info_from_urls(urls)

            data.requires_dist = info.requires_dist

            if not data.requires_python:
                data.requires_python = info.requires_python

        return data.asdict()

    def _get(self, endpoint: str) -> dict | None:
        try:
            json_response = self.session.get(self._base_url + endpoint)
        except requests.exceptions.TooManyRedirects:
            # Cache control redirect loop.
            # We try to remove the cache and try again
            self._cache_control_cache.delete(self._base_url + endpoint)
            json_response = self.session.get(self._base_url + endpoint)

        if json_response.status_code == 404:
            return None

        return json_response.json()

    def _get_info_from_urls(self, urls: dict[str, list[str]]) -> PackageInfo:
        # Checking wheels first as they are more likely to hold
        # the necessary information
        if "bdist_wheel" in urls:
            # Check for a universal wheel
            wheels = urls["bdist_wheel"]

            universal_wheel = None
            universal_python2_wheel = None
            universal_python3_wheel = None
            platform_specific_wheels = []
            for wheel in wheels:
                link = Link(wheel)
                m = wheel_file_re.match(link.filename)
                if not m:
                    continue

                pyver = m.group("pyver")
                abi = m.group("abi")
                plat = m.group("plat")
                if abi == "none" and plat == "any":
                    # Universal wheel
                    if pyver == "py2.py3":
                        # Any Python
                        universal_wheel = wheel
                    elif pyver == "py2":
                        universal_python2_wheel = wheel
                    else:
                        universal_python3_wheel = wheel
                else:
                    platform_specific_wheels.append(wheel)

            if universal_wheel is not None:
                return self._get_info_from_wheel(universal_wheel)

            info = None
            if universal_python2_wheel and universal_python3_wheel:
                info = self._get_info_from_wheel(universal_python2_wheel)

                py3_info = self._get_info_from_wheel(universal_python3_wheel)
                if py3_info.requires_dist:
                    if not info.requires_dist:
                        info.requires_dist = py3_info.requires_dist

                        return info

                    py2_requires_dist = {
                        Dependency.create_from_pep_508(r).to_pep_508()
                        for r in info.requires_dist
                    }
                    py3_requires_dist = {
                        Dependency.create_from_pep_508(r).to_pep_508()
                        for r in py3_info.requires_dist
                    }
                    base_requires_dist = py2_requires_dist & py3_requires_dist
                    py2_only_requires_dist = py2_requires_dist - py3_requires_dist
                    py3_only_requires_dist = py3_requires_dist - py2_requires_dist

                    # Normalizing requires_dist
                    requires_dist = list(base_requires_dist)
                    for requirement in py2_only_requires_dist:
                        dep = Dependency.create_from_pep_508(requirement)
                        dep.marker = dep.marker.intersect(
                            parse_marker("python_version == '2.7'")
                        )
                        requires_dist.append(dep.to_pep_508())

                    for requirement in py3_only_requires_dist:
                        dep = Dependency.create_from_pep_508(requirement)
                        dep.marker = dep.marker.intersect(
                            parse_marker("python_version >= '3'")
                        )
                        requires_dist.append(dep.to_pep_508())

                    info.requires_dist = sorted(set(requires_dist))

            if info:
                return info

            # Prefer non platform specific wheels
            if universal_python3_wheel:
                return self._get_info_from_wheel(universal_python3_wheel)

            if universal_python2_wheel:
                return self._get_info_from_wheel(universal_python2_wheel)

            if platform_specific_wheels and "sdist" not in urls:
                # Pick the first wheel available and hope for the best
                return self._get_info_from_wheel(platform_specific_wheels[0])

        return self._get_info_from_sdist(urls["sdist"][0])

    def _get_info_from_wheel(self, url: str) -> PackageInfo:
        from poetry.inspection.info import PackageInfo

        wheel_name = urllib.parse.urlparse(url).path.rsplit("/")[-1]
        self._log(f"Downloading wheel: {wheel_name}", level="debug")
        filename = os.path.basename(wheel_name)

        with temporary_directory() as temp_dir:
            filepath = Path(temp_dir) / filename
            self._download(url, str(filepath))

            return PackageInfo.from_wheel(filepath)

    def _get_info_from_sdist(self, url: str) -> PackageInfo:
        from poetry.inspection.info import PackageInfo

        sdist_name = urllib.parse.urlparse(url).path
        self._log(f"Downloading sdist: {sdist_name.rsplit('/')[-1]}", level="debug")
        filename = os.path.basename(sdist_name)

        with temporary_directory() as temp_dir:
            filepath = Path(temp_dir) / filename
            self._download(url, str(filepath))

            return PackageInfo.from_sdist(filepath)

    def _download(self, url: str, dest: str) -> None:
        return download_file(url, dest, session=self.session)

    def _log(self, msg: str, level: str = "info") -> None:
        getattr(logger, level)(f"<debug>{self._name}:</debug> {msg}")

    def get_sha_hash_from_link(self, link: Link) -> str | None:
        """Get sha256|384|512 hash for a file from the provided link.

        If the hash type included in the link is not sha256|384|512,
        convert it to sha256.

        """
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

        return file_hash
