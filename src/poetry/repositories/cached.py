from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Any

from cachy import CacheManager
from packaging.utils import canonicalize_name
from poetry.core.constraints.version import parse_constraint

from poetry.config.config import Config
from poetry.repositories.repository import Repository


if TYPE_CHECKING:
    from packaging.utils import NormalizedName
    from poetry.core.constraints.version import Version
    from poetry.core.packages.package import Package

    from poetry.inspection.info import PackageInfo


class CachedRepository(Repository, ABC):
    CACHE_VERSION = parse_constraint("1.1.0")

    def __init__(
        self, name: str, disable_cache: bool = False, config: Config | None = None
    ) -> None:
        super().__init__(name)
        self._disable_cache = disable_cache
        self._cache_dir = (config or Config.create()).repository_cache_directory / name
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

    @abstractmethod
    def _get_release_info(
        self, name: NormalizedName, version: Version
    ) -> dict[str, Any]:
        raise NotImplementedError()

    def get_release_info(self, name: NormalizedName, version: Version) -> PackageInfo:
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

    def package(
        self,
        name: str,
        version: Version,
        extras: list[str] | None = None,
    ) -> Package:
        return self.get_release_info(canonicalize_name(name), version).to_package(
            name=name, extras=extras
        )
