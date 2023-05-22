from __future__ import annotations

import uuid

from typing import TYPE_CHECKING
from typing import TypeVar

import pytest

from poetry.utils.cache import FileCache


if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.monkeypatch import MonkeyPatch

    from tests.conftest import Config

T = TypeVar("T")


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
) -> FileCache[dict[str, str]]:
    cache: FileCache[dict[str, str]] = FileCache(
        path=repository_cache_dir / repository_one
    )

    cache.remember(
        "cachy:0.1", lambda: {"name": "cachy", "version": "0.1"}, minutes=None
    )
    cache.remember("cleo:0.2", lambda: {"name": "cleo", "version": "0.2"}, minutes=None)
    return cache
