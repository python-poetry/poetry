from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar
from typing import Union
from unittest.mock import Mock

import pytest

from cachy import CacheManager

from poetry.utils.cache import FileCache


if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.monkeypatch import MonkeyPatch
    from pytest import FixtureRequest
    from pytest_mock import MockerFixture

    from tests.conftest import Config


FILE_CACHE = Union[FileCache, CacheManager]
T = TypeVar("T")


@pytest.fixture
def repository_cache_dir(monkeypatch: MonkeyPatch, config: Config) -> Path:
    return config.repository_cache_directory


def patch_cachy(cache: CacheManager) -> CacheManager:
    old_put = cache.put
    old_remember = cache.remember

    def new_put(key: str, value: Any, minutes: int | None = None) -> Any:
        if minutes is not None:
            return old_put(key, value, minutes=minutes)
        else:
            return cache.forever(key, value)

    cache.put = new_put

    def new_remember(key: str, value: Any, minutes: int | None = None) -> Any:
        if minutes is not None:
            return old_remember(key, value, minutes=minutes)
        else:
            return cache.remember_forever(key, value)

    cache.remember = new_remember
    return cache


@pytest.fixture
def cachy_file_cache(repository_cache_dir: Path) -> CacheManager:
    cache = CacheManager(
        {
            "default": "cache",
            "serializer": "json",
            "stores": {
                "cache": {"driver": "file", "path": str(repository_cache_dir / "cache")}
            },
        }
    )
    return patch_cachy(cache)


@pytest.fixture
def poetry_file_cache(repository_cache_dir: Path) -> FileCache[T]:
    return FileCache(repository_cache_dir / "cache")


@pytest.fixture
def cachy_dict_cache() -> CacheManager:
    cache = CacheManager(
        {
            "default": "cache",
            "serializer": "json",
            "stores": {"cache": {"driver": "dict"}},
        }
    )
    return patch_cachy(cache)


def test_cache_validates(repository_cache_dir: Path) -> None:
    with pytest.raises(ValueError) as e:
        FileCache(repository_cache_dir / "cache", hash_type="unknown")
    assert str(e.value) == "FileCache.hash_type is unknown value: 'unknown'."


@pytest.mark.parametrize("cache_name", ["cachy_file_cache", "poetry_file_cache"])
def test_cache_get_put_has(cache_name: str, request: FixtureRequest) -> None:
    cache = request.getfixturevalue(cache_name)
    cache.put("key1", "value")
    cache.put("key2", {"a": ["json-encoded", "value"]})

    assert cache.get("key1") == "value"
    assert cache.get("key2") == {"a": ["json-encoded", "value"]}
    assert cache.has("key1")
    assert cache.has("key2")
    assert not cache.has("key3")


@pytest.mark.parametrize("cache_name", ["cachy_file_cache", "poetry_file_cache"])
def test_cache_forget(cache_name: str, request: FixtureRequest) -> None:
    cache = request.getfixturevalue(cache_name)
    cache.put("key1", "value")
    cache.put("key2", "value")

    assert cache.has("key1")
    assert cache.has("key2")

    cache.forget("key1")

    assert not cache.has("key1")
    assert cache.has("key2")


@pytest.mark.parametrize("cache_name", ["cachy_file_cache", "poetry_file_cache"])
def test_cache_flush(cache_name: str, request: FixtureRequest) -> None:
    cache = request.getfixturevalue(cache_name)
    cache.put("key1", "value")
    cache.put("key2", "value")

    assert cache.has("key1")
    assert cache.has("key2")

    cache.flush()

    assert not cache.has("key1")
    assert not cache.has("key2")


@pytest.mark.parametrize("cache_name", ["cachy_file_cache", "poetry_file_cache"])
def test_cache_remember(
    cache_name: str, request: FixtureRequest, mocker: MockerFixture
) -> None:
    cache = request.getfixturevalue(cache_name)

    method = Mock(return_value="value2")
    cache.put("key1", "value1")
    assert cache.remember("key1", method) == "value1"
    method.assert_not_called()

    assert cache.remember("key2", method) == "value2"
    method.assert_called()


@pytest.mark.parametrize("cache_name", ["cachy_file_cache", "poetry_file_cache"])
def test_cache_get_limited_minutes(
    mocker: MockerFixture,
    cache_name: str,
    request: FixtureRequest,
) -> None:
    cache = request.getfixturevalue(cache_name)

    # needs to be 10 digits because cachy assumes it's a 10-digit int.
    start_time = 1111111111

    mocker.patch("time.time", return_value=start_time)
    cache.put("key1", "value", minutes=5)
    cache.put("key2", "value", minutes=5)

    assert cache.get("key1") is not None
    assert cache.get("key2") is not None

    mocker.patch("time.time", return_value=start_time + 5 * 60 + 1)
    # check to make sure that the cache deletes for has() and get()
    assert not cache.has("key1")
    assert cache.get("key2") is None


def test_cachy_compatibility(
    cachy_file_cache: CacheManager, poetry_file_cache: FileCache[T]
) -> None:
    """
    The new file cache should be able to support reading legacy caches.
    """
    test_str = "value"
    test_obj = {"a": ["json", "object"]}
    cachy_file_cache.put("key1", test_str)
    cachy_file_cache.put("key2", test_obj)

    assert poetry_file_cache.get("key1") == test_str
    assert poetry_file_cache.get("key2") == test_obj

    poetry_file_cache.put("key3", test_str)
    poetry_file_cache.put("key4", test_obj)

    assert cachy_file_cache.get("key3") == test_str
    assert cachy_file_cache.get("key4") == test_obj
