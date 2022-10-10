from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.core.constraints.version import Version


if TYPE_CHECKING:
    from poetry.core.packages.package import Package

    from poetry.repositories import Pool


class VersionSelector:
    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    def find_best_candidate(
        self,
        package_name: str,
        target_package_version: str | None = None,
        allow_prereleases: bool = False,
        source: str | None = None,
    ) -> Package | None:
        """
        Given a package name and optional version,
        returns the latest Package that matches
        """
        from poetry.factory import Factory

        dependency = Factory.create_dependency(
            package_name,
            {
                "version": target_package_version or "*",
                "allow-prereleases": allow_prereleases,
                "source": source,
            },
        )
        candidates = self._pool.find_packages(dependency)
        only_prereleases = all(c.version.is_unstable() for c in candidates)

        if not candidates:
            return None

        package = None
        for candidate in candidates:
            if (
                candidate.is_prerelease()
                and not dependency.allows_prereleases()
                and not only_prereleases
            ):
                continue

            # Select highest version of the two
            if package is None or package.version < candidate.version:
                package = candidate

        return package

    def find_recommended_require_version(self, package: Package) -> str:
        version = package.version

        return self._transform_version(version.text, package.pretty_version)

    def _transform_version(self, version: str, pretty_version: str) -> str:
        try:
            return f"^{Version.parse(version).to_string()}"
        except ValueError:
            return pretty_version
