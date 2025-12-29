from __future__ import annotations

from typing import Any

import pytest

from packaging.utils import NormalizedName
from packaging.utils import canonicalize_name
from poetry.core.constraints.version import Version

from poetry.inspection.info import PackageInfo
from poetry.repositories.cached_repository import CachedRepository


class MockCachedRepository(CachedRepository):
    def _get_release_info(
        self, name: NormalizedName, version: Version
    ) -> dict[str, Any]:
        raise NotImplementedError


@pytest.fixture
def release_info() -> PackageInfo:
    return PackageInfo(
        name="mylib",
        version="1.0",
        summary="",
        requires_dist=[],
        requires_python=">=3.9",
        files=[
            {
                "file": "mylib-1.0-py3-none-any.whl",
                "hash": "sha256:dummyhashvalue1234567890abcdef",
            },
            {
                "file": "mylib-1.0.tar.gz",
                "hash": "sha256:anotherdummyhashvalueabcdef1234567890",
            },
        ],
        cache_version=str(CachedRepository.CACHE_VERSION),
    )


@pytest.fixture
def outdated_release_info() -> PackageInfo:
    return PackageInfo(
        name="mylib",
        version="1.0",
        summary="",
        requires_dist=[],
        requires_python=">=3.9",
        files=[
            {
                "file": "mylib-1.0-py3-none-any.whl",
                "hash": "sha256:dummyhashvalue1234567890abcdef",
            }
        ],
        cache_version=str(CachedRepository.CACHE_VERSION),
    )


@pytest.mark.parametrize("disable_cache", [False, True])
def test_get_release_info_cache(
    release_info: PackageInfo, outdated_release_info: PackageInfo, disable_cache: bool
) -> None:
    repo = MockCachedRepository("mock", disable_cache=disable_cache)
    repo._get_release_info = lambda name, version: outdated_release_info.asdict()  # type: ignore[method-assign]

    name = canonicalize_name("mylib")
    version = Version.parse("1.0")
    assert len(repo.get_release_info(name, version).files) == 1

    # without disable_cache: cached value is returned even if the underlying data has changed
    # with disable_cache: cached value is ignored and updated data is returned
    repo._get_release_info = lambda name, version: release_info.asdict()  # type: ignore[method-assign]
    assert len(repo.get_release_info(name, version).files) == (
        2 if disable_cache else 1
    )

    # after clearing the cache entry, updated data is returned
    repo.forget(name, version)
    assert len(repo.get_release_info(name, version).files) == 2
