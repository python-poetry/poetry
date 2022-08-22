from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cleo.testers.application_tester import ApplicationTester

from poetry.console.application import Application


if TYPE_CHECKING:
    from pathlib import Path

    from cachy import CacheManager


@pytest.fixture
def tester() -> ApplicationTester:
    app = Application()

    tester = ApplicationTester(app)
    return tester


def test_cache_clear_all(
    tester: ApplicationTester,
    repository_one: str,
    repository_cache_dir: Path,
    cache: CacheManager,
):
    exit_code = tester.execute(f"cache clear {repository_one} --all", inputs="yes")

    assert exit_code == 0
    assert tester.io.fetch_output() == ""
    # ensure directory is empty
    assert not any((repository_cache_dir / repository_one).iterdir())
    assert not cache.has("cachy:0.1")
    assert not cache.has("cleo:0.2")


def test_cache_clear_all_assume_yes(
    tester: ApplicationTester,
    repository_one: str,
    repository_cache_dir: Path,
    cache: CacheManager,
):
    exit_code = tester.execute(f"cache clear {repository_one} --all --assume-yes")

    assert exit_code == 0
    assert tester.io.fetch_output() == "Deleting 2 entries.\n"
    # ensure directory is empty
    assert not any((repository_cache_dir / repository_one).iterdir())
    assert not cache.has("cachy:0.1")
    assert not cache.has("cleo:0.2")


def test_cache_clear_all_no(
    tester: ApplicationTester,
    repository_one: str,
    repository_cache_dir: Path,
    cache: CacheManager,
):
    exit_code = tester.execute(f"cache clear {repository_one} --all", inputs="no")

    assert exit_code == 0
    assert tester.io.fetch_output() == ""
    # ensure directory is not empty
    assert any((repository_cache_dir / repository_one).iterdir())
    assert cache.has("cachy:0.1")
    assert cache.has("cleo:0.2")


def test_cache_clear_pkg(
    tester: ApplicationTester,
    repository_one: str,
    cache: CacheManager,
):
    exit_code = tester.execute(f"cache clear {repository_one}:cachy:0.1", inputs="yes")

    assert exit_code == 0
    assert tester.io.fetch_output() == ""
    assert not cache.has("cachy:0.1")
    assert cache.has("cleo:0.2")


def test_cache_clear_pkg_assume_yes(
    tester: ApplicationTester,
    repository_one: str,
    cache: CacheManager,
):
    exit_code = tester.execute(f"cache clear {repository_one}:cachy:0.1 -y")

    assert exit_code == 0
    assert tester.io.fetch_output() == "Deleting cache entry cachy:0.1\n"
    assert not cache.has("cachy:0.1")
    assert cache.has("cleo:0.2")


def test_cache_clear_pkg_no(
    tester: ApplicationTester,
    repository_one: str,
    cache: CacheManager,
):
    exit_code = tester.execute(f"cache clear {repository_one}:cachy:0.1", inputs="no")

    assert exit_code == 0
    assert tester.io.fetch_output() == ""
    assert cache.has("cachy:0.1")
    assert cache.has("cleo:0.2")
