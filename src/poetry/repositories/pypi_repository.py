from __future__ import annotations

import logging

from collections import defaultdict
from typing import TYPE_CHECKING
from typing import Any

import requests

from cachecontrol.controller import logger as cache_control_logger
from html5lib.html5parser import parse
from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link
from poetry.core.version.exceptions import InvalidVersion

from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.http import HTTPRepository
from poetry.utils._compat import to_str


cache_control_logger.setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from poetry.core.packages.dependency import Dependency


class PyPiRepository(HTTPRepository):
    def __init__(
        self,
        url: str = "https://pypi.org/",
        disable_cache: bool = False,
        fallback: bool = True,
    ) -> None:
        super().__init__(
            "PyPI", url.rstrip("/") + "/simple/", disable_cache=disable_cache
        )

        self._base_url = url
        self._fallback = fallback

    def find_packages(self, dependency: Dependency) -> list[Package]:
        """
        Find packages on the remote server.
        """
        constraint, allow_prereleases = self._get_constraints_from_dependency(
            dependency
        )

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

            if constraint.allows(package.version):
                packages.append(package)

        self._log(
            f"{len(packages)} packages found for {dependency.name} {constraint!s}",
            level="debug",
        )

        return packages or ignored_pre_release_packages

    def search(self, query: str) -> list[Package]:
        results = []

        search = {"q": query}

        response = requests.session().get(self._base_url + "search", params=search)
        content = parse(response.content, namespaceHTMLElements=False)
        for result in content.findall(".//*[@class='package-snippet']"):
            name_element = result.find("h3/*[@class='package-snippet__name']")
            version_element = result.find("h3/*[@class='package-snippet__version']")

            if (
                name_element is None
                or version_element is None
                or not name_element.text
                or not version_element.text
            ):
                continue

            name = name_element.text
            version = version_element.text

            description_element = result.find(
                "p[@class='package-snippet__description']"
            )
            description = (
                description_element.text
                if description_element is not None and description_element.text
                else ""
            )

            try:
                package = Package(name, version)
                package.description = to_str(description.strip())
                results.append(package)
            except InvalidVersion:
                self._log(
                    f'Unable to parse version "{version}" for the {name} package,'
                    " skipping",
                    level="debug",
                )

        return results

    def get_package_info(self, name: str) -> dict[str, Any]:
        """
        Return the package information given its name.

        The information is returned from the cache if it exists
        or retrieved from the remote server.
        """
        if self._disable_cache:
            return self._get_package_info(name)

        package_info: dict[str, Any] = self._cache.store("packages").remember_forever(
            name, lambda: self._get_package_info(name)
        )
        return package_info

    def _get_package_info(self, name: str) -> dict[str, Any]:
        data = self._get(f"pypi/{name}/json")
        if data is None:
            raise PackageNotFound(f"Package [{name}] not found.")

        return data

    def find_links_for_package(self, package: Package) -> list[Link]:
        json_data = self._get(f"pypi/{package.name}/{package.version}/json")
        if json_data is None:
            return []

        links = []
        for url in json_data["urls"]:
            h = f"sha256={url['digests']['sha256']}"
            links.append(Link(url["url"] + "#" + h))

        return links

    def _get_release_info(
        self, name: str, version: str
    ) -> dict[str, str | list[str] | None]:
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

    def _get(self, endpoint: str) -> dict[str, Any] | None:
        try:
            json_response = self.session.get(
                self._base_url + endpoint, raise_for_status=False
            )
        except requests.exceptions.TooManyRedirects:
            # Cache control redirect loop.
            # We try to remove the cache and try again
            self.session.delete_cache(self._base_url + endpoint)
            json_response = self.session.get(
                self._base_url + endpoint, raise_for_status=False
            )

        if json_response.status_code == 404:
            return None

        json: dict[str, Any] = json_response.json()
        return json
