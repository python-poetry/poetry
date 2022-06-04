from __future__ import annotations

import uuid

from typing import TYPE_CHECKING

import pytest

from cachy import CacheManager


if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.monkeypatch import MonkeyPatch

    from tests.conftest import Config


@pytest.fixture
def repository_cache_dir(monkeypatch: MonkeyPatch, config: Config) -> Path:
    return config.repository_cache_directory


@pytest.fixture
def repository_one() -> str:
    return f"01_{uuid.uuid4()}"


@pytest.fixture
def repository_two() -> str:
    return f"02_{uuid.uuid4()}"


@pytest.fixture
def mock_caches(
    repository_cache_dir: Path,
    repository_one: str,
    repository_two: str,
) -> None:
    (repository_cache_dir / repository_one).mkdir(parents=True)
    (repository_cache_dir / repository_two).mkdir(parents=True)


@pytest.fixture
def cache(
    repository_cache_dir: Path,
    repository_one: str,
    mock_caches: None,
) -> CacheManager:
    cache = CacheManager(
        {
            "default": repository_one,
            "serializer": "json",
            "stores": {
                repository_one: {
                    "driver": "file",
                    "path": str(repository_cache_dir / repository_one),
                }
            },
        }
    )
    cache.remember_forever("cachy:0.1", lambda: {"name": "cachy", "version": "0.1"})
    cache.remember_forever("cleo:0.2", lambda: {"name": "cleo", "version": "0.2"})
    return cache
