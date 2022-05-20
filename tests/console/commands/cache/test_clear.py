from __future__ import annotations

import uuid

from typing import TYPE_CHECKING

import pytest

from cachy import CacheManager


if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.monkeypatch import MonkeyPatch
    from cleo.testers.command_tester import CommandTester

    from tests.types import CommandTesterFactory


@pytest.fixture
def repository_cache_dir(monkeypatch: MonkeyPatch, tmpdir: Path) -> Path:
    from pathlib import Path

    import poetry.locations

    path = Path(str(tmpdir))
    monkeypatch.setattr(poetry.locations, "REPOSITORY_CACHE_DIR", path)
    return path


@pytest.fixture
def repository() -> str:
    return f"01_{uuid.uuid4()}"


@pytest.fixture
def cache(repository_cache_dir: Path, repository: str) -> CacheManager:
    cache = CacheManager(
        {
            "default": repository,
            "serializer": "json",
            "stores": {
                repository: {
                    "driver": "file",
                    "path": str(repository_cache_dir / repository),
                }
            },
        }
    )
    return cache


@pytest.fixture
def mock_caches(
    repository_cache_dir: Path,
    repository: str,
    cache: CacheManager,
) -> None:
    (repository_cache_dir / repository).mkdir()
    cache.remember_forever("cachy:0.1", lambda: {"name": "cachy", "version": "0.1"})
    cache.remember_forever("cleo:0.2", lambda: {"name": "cleo", "version": "0.2"})


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory):
    return command_tester_factory("cache clear")


def test_cache_clear_all(
    tester: CommandTester,
    repository: str,
    repository_cache_dir: Path,
    mock_caches: None,
):
    tester.execute(f"{repository} --all", inputs="yes")

    assert tester.io.fetch_output() == ""
    # ensure directory is empty
    assert not any((repository_cache_dir / repository).iterdir())


def test_cache_clear_all_no(
    tester: CommandTester,
    repository: str,
    repository_cache_dir: Path,
    cache: CacheManager,
    mock_caches: None,
):
    tester.execute(f"{repository} --all", inputs="no")

    assert tester.io.fetch_output() == ""
    # ensure directory is not empty
    assert any((repository_cache_dir / repository).iterdir())


def test_cache_clear_pkg(
    tester: CommandTester,
    repository: str,
    repository_cache_dir: Path,
    cache: CacheManager,
    mock_caches: None,
):
    tester.execute(f"{repository}:cachy:0.1", inputs="yes")

    assert tester.io.fetch_output() == ""
    assert not cache.has("cachy:0.1")
    assert cache.has("cleo:0.2")


def test_cache_clear_pkg_no(
    tester: CommandTester,
    repository: str,
    repository_cache_dir: Path,
    cache: CacheManager,
    mock_caches: None,
):
    tester.execute(f"{repository}:cachy:0.1", inputs="no")

    assert tester.io.fetch_output() == ""
    assert cache.has("cachy:0.1")
