import uuid

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from _pytest.monkeypatch import MonkeyPatch
from cachy import CacheManager


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def repository_cache_dir(monkeypatch: MonkeyPatch, tmpdir: Path) -> Path:
    from pathlib import Path

    import poetry.locations

    path = Path(str(tmpdir))
    monkeypatch.setattr(poetry.locations, "REPOSITORY_CACHE_DIR", path)
    return path


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
    (repository_cache_dir / repository_one).mkdir()
    (repository_cache_dir / repository_two).mkdir()


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
