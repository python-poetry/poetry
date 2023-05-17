from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from packaging.utils import NormalizedName
from poetry.core.constraints.version import Version

from poetry.inspection.info import PackageInfo
from poetry.repositories.cached_repository import CachedRepository
from poetry.utils.cache import FileCache


if TYPE_CHECKING:
    from poetry.config.config import Config


class TestCachedRepository(CachedRepository):
    __test__ = False

    def _get_release_info(self, name: NormalizedName, version: Version) -> PackageInfo:
        return PackageInfo(name=name, version=str(version))


def test_cached_repository_returns_package_info(config: Config) -> None:
    repo = TestCachedRepository(name="foo", config=config)

    package_info = repo.get_release_info(NormalizedName("bar"), Version.parse("1.0.0"))

    assert package_info.name == "bar"
    assert package_info.version == "1.0.0"


def test_cached_repository_populates_cache(config: Config) -> None:
    repo = TestCachedRepository(name="foo", config=config)

    repo.get_release_info(NormalizedName("bar"), Version.parse("1.0.0"))

    assert repo._release_cache.has("bar:1.0.0")
    cached = repo._release_cache.get("bar:1.0.0")
    assert cached and cached["_cache_version"] == str(repo.CACHE_VERSION)


def test_cached_repository_disable_cache(config: Config) -> None:
    repo = TestCachedRepository(name="foo", config=config, disable_cache=True)
    release_cache = MagicMock(spec=FileCache)
    repo._release_cache = release_cache

    repo.get_release_info(NormalizedName("bar"), Version.parse("1.0.0"))

    release_cache.remember.assert_not_called()
    release_cache.get.assert_not_called()
    release_cache.put.assert_not_called()
