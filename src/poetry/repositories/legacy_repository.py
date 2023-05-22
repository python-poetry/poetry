from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from poetry.core.packages.package import Package

from poetry.inspection.info import PackageInfo
from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.http_repository import HTTPRepository
from poetry.repositories.link_sources.html import SimpleRepositoryPage


if TYPE_CHECKING:
    from packaging.utils import NormalizedName
    from poetry.core.constraints.version import Version
    from poetry.core.constraints.version import VersionConstraint
    from poetry.core.packages.utils.link import Link

    from poetry.config.config import Config


class LegacyRepository(HTTPRepository):
    def __init__(
        self,
        name: str,
        url: str,
        config: Config | None = None,
        disable_cache: bool = False,
    ) -> None:
        if name == "pypi":
            raise ValueError("The name [pypi] is reserved for repositories")

        super().__init__(name, url.rstrip("/"), config, disable_cache)

    @property
    def packages(self) -> list[Package]:
        # LegacyRepository._packages is not populated and other implementations
        # implicitly rely on this (e.g. Pool.search via
        # LegacyRepository.search). To avoid special-casing Pool or changing
        # behavior, we stub and return an empty list.
        #
        # TODO: Rethinking search behaviour and design.
        # Ref: https://github.com/python-poetry/poetry/issues/2446 and
        # https://github.com/python-poetry/poetry/pull/6669#discussion_r990874908.
        return []

    def package(
        self, name: str, version: Version, extras: list[str] | None = None
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
            index = self._packages.index(Package(name, version))

            return self._packages[index]
        except ValueError:
            package = super().package(name, version, extras)
            package._source_type = "legacy"
            package._source_url = self._url
            package._source_reference = self.name

            return package

    def find_links_for_package(self, package: Package) -> list[Link]:
        try:
            page = self.get_page(package.name)
        except PackageNotFound:
            return []

        return list(page.links_for_version(package.name, package.version))

    def _find_packages(
        self, name: NormalizedName, constraint: VersionConstraint
    ) -> list[Package]:
        """
        Find packages on the remote server.
        """
        try:
            page = self.get_page(name)
        except PackageNotFound:
            self._log(f"No packages found for {name}", level="debug")
            return []

        versions = [
            (version, page.yanked(name, version))
            for version in page.versions(name)
            if constraint.allows(version)
        ]

        return [
            Package(
                name,
                version,
                source_type="legacy",
                source_reference=self.name,
                source_url=self._url,
                yanked=yanked,
            )
            for version, yanked in versions
        ]

    def _get_release_info(
        self, name: NormalizedName, version: Version
    ) -> dict[str, Any]:
        page = self.get_page(name)

        links = list(page.links_for_version(name, version))
        yanked = page.yanked(name, version)

        return self._links_to_data(
            links,
            PackageInfo(
                name=name,
                version=version.text,
                summary="",
                requires_dist=[],
                requires_python=None,
                files=[],
                yanked=yanked,
                cache_version=str(self.CACHE_VERSION),
            ),
        )

    def _get_page(self, name: NormalizedName) -> SimpleRepositoryPage:
        response = self._get_response(f"/{name}/")
        if not response:
            raise PackageNotFound(f"Package [{name}] not found.")
        return SimpleRepositoryPage(response.url, response.text)
