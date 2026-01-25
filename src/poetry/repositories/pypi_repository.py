from __future__ import annotations

import contextlib
import logging

from typing import TYPE_CHECKING
from typing import Any

import requests
import requests.adapters

from cachecontrol.controller import logger as cache_control_logger
from poetry.core.packages.dependency import Dependency
from poetry.core.packages.package import Package
from poetry.core.version.exceptions import InvalidVersionError
from poetry.core.version.requirements import InvalidRequirementError

from poetry.repositories.exceptions import PackageNotFoundError
from poetry.repositories.http_repository import HTTPRepository
from poetry.repositories.link_sources.json import SimpleJsonPage
from poetry.repositories.parsers.pypi_search_parser import SearchResultParser
from poetry.utils.constants import REQUESTS_TIMEOUT


cache_control_logger.setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from packaging.utils import NormalizedName
    from poetry.core.constraints.version import VersionConstraint

    from poetry.config.config import Config


class PyPiRepository(HTTPRepository):
    def __init__(
        self,
        url: str = "https://pypi.org/",
        *,
        config: Config | None = None,
        disable_cache: bool = False,
        pool_size: int = requests.adapters.DEFAULT_POOLSIZE,
        fallback: bool = True,
    ) -> None:
        super().__init__(
            "PyPI",
            url.rstrip("/") + "/simple/",
            config=config,
            disable_cache=disable_cache,
            pool_size=pool_size,
        )

        self._base_url = url

    def search(self, query: str | list[str]) -> list[Package]:
        results = []

        response = requests.get(
            self._base_url + "search", params={"q": query}, timeout=REQUESTS_TIMEOUT
        )
        parser = SearchResultParser()
        parser.feed(response.text)

        for result in parser.results:
            try:
                package = Package(result.name, result.version)
                package.description = result.description.strip()
                results.append(package)
            except InvalidVersionError:
                self._log(
                    f'Unable to parse version "{result.version}" for the'
                    f" {result.name} package, skipping",
                    level="debug",
                )

        if not results:
            # in cases like PyPI search might not be available, we fallback to explicit searches
            # to allow for a nicer ux rather than finding nothing at all
            # see: https://discuss.python.org/t/fastly-interfering-with-pypi-search/73597/6
            #
            tokens = query if isinstance(query, list) else [query]
            for token in tokens:
                with contextlib.suppress(InvalidRequirementError):
                    results.extend(
                        self.find_packages(Dependency.create_from_pep_508(token))
                    )

        return results

    def get_package_info(self, name: NormalizedName) -> dict[str, Any]:
        """
        Return the package information given its name.

        The information is returned from the cache if it exists
        or retrieved from the remote server.
        """
        return self._get_package_info(name)

    def _find_packages(
        self, name: NormalizedName, constraint: VersionConstraint
    ) -> list[Package]:
        """
        Find packages on the remote server.
        """
        try:
            json_page = self.get_page(name)
        except PackageNotFoundError:
            self._log(f"No packages found for {name}", level="debug")
            return []

        versions = [
            (version, json_page.yanked(name, version))
            for version in json_page.versions(name)
            if constraint.allows(version)
        ]

        return [Package(name, version, yanked=yanked) for version, yanked in versions]

    def _get_package_info(self, name: NormalizedName) -> dict[str, Any]:
        headers = {"Accept": "application/vnd.pypi.simple.v1+json"}
        info = self._get(f"simple/{name}/", headers=headers)
        if info is None:
            raise PackageNotFoundError(f"Package [{name}] not found.")

        return info

    def _get_page(self, name: NormalizedName) -> SimpleJsonPage:
        source = self._base_url + f"simple/{name}/"
        info = self.get_package_info(name)
        return SimpleJsonPage(source, info)

    def _get(
        self, endpoint: str, headers: dict[str, str] | None = None
    ) -> dict[str, Any] | None:
        try:
            json_response = self.session.get(
                self._base_url + endpoint,
                raise_for_status=False,
                timeout=REQUESTS_TIMEOUT,
                headers=headers,
            )
        except requests.exceptions.TooManyRedirects:
            # Cache control redirect loop.
            # We try to remove the cache and try again
            self.session.delete_cache(self._base_url + endpoint)
            json_response = self.session.get(
                self._base_url + endpoint,
                raise_for_status=False,
                timeout=REQUESTS_TIMEOUT,
                headers=headers,
            )

        if json_response.status_code != 200:
            return None

        json: dict[str, Any] = json_response.json()
        return json

    @staticmethod
    def _get_yanked(json_data: dict[str, Any]) -> str | bool:
        if json_data.get("yanked", False):
            return json_data.get("yanked_reason") or True
        return False
