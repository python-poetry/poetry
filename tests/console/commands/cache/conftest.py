from __future__ import annotations

import uuid

from typing import TYPE_CHECKING

import pytest

from poetry.utils.cache import FileCache


if TYPE_CHECKING:
    from pathlib import Path

    from tests.conftest import Config


@pytest.fixture
def repository_cache_dir(config: Config) -> Path:
    return config.repository_cache_directory


@pytest.fixture
def repositories() -> list[str]:
    return [f"01_{uuid.uuid4()}", f"02_{uuid.uuid4()}"]


@pytest.fixture
def repository_dirs(
    repository_cache_dir: Path,
    repositories: list[str],
) -> list[Path]:
    return [
        repository_cache_dir / repositories[0],
        repository_cache_dir / repositories[1],
    ]


@pytest.fixture
def caches(
    repository_dirs: list[Path],
) -> list[FileCache[dict[str, str]]]:
    repository_dirs[0].mkdir(parents=True)
    repository_dirs[1].mkdir(parents=True)

    caches: list[FileCache[dict[str, str]]] = [
        FileCache(path=repository_dirs[0]),
        FileCache(path=repository_dirs[1]),
    ]

    caches[0].remember(
        "cachy:0.1", lambda: {"name": "cachy", "version": "0.1"}, minutes=None
    )
    caches[0].remember(
        "cleo:0.2", lambda: {"name": "cleo", "version": "0.2"}, minutes=None
    )

    caches[1].remember(
        "cachy:0.1", lambda: {"name": "cachy", "version": "0.1"}, minutes=None
    )
    # different version of same package, other entry than in first cache
    caches[1].remember(
        "cashy:0.2", lambda: {"name": "cashy", "version": "0.2"}, minutes=None
    )

    return caches
