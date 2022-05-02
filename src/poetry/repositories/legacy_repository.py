from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from poetry.core.packages.package import Package
from poetry.core.semver.version import Version

from poetry.inspection.info import PackageInfo
from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.http import HTTPRepository
from poetry.repositories.link_sources.html import SimpleRepositoryPage
from poetry.utils.helpers import canonicalize_name


if TYPE_CHECKING:
    from poetry.core.packages.dependency import Dependency
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

    def find_packages(self, dependency: Dependency) -> list[Package]:
        packages = []
        constraint, allow_prereleases = self._get_constraints_from_dependency(
            dependency
        )

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
            for version in page.versions(dependency.name):
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
        self, name: str, version: str, extras: list[str] | None = None
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

    def find_links_for_package(self, package: Package) -> list[Link]:
        page = self._get_page(f"/{package.name.replace('.', '-')}/")
        if page is None:
            return []

        return list(page.links_for_version(package.name, package.version))

    def _get_release_info(self, name: str, version: str) -> dict[str, Any]:
        page = self._get_page(f"/{canonicalize_name(name).replace('.', '-')}/")
        if page is None:
            raise PackageNotFound(f'No package named "{name}"')

        links = list(page.links_for_version(name, Version.parse(version)))

        return self._links_to_data(
            links,
            PackageInfo(
                name=name,
                version=version,
                summary="",
                platform=None,
                requires_dist=[],
                requires_python=None,
                files=[],
                cache_version=str(self.CACHE_VERSION),
            ),
        )

    def _get_page(self, endpoint: str) -> SimpleRepositoryPage | None:
        response = self._get_response(endpoint)
        if not response:
            return None
        return SimpleRepositoryPage(response.url, response.text)
