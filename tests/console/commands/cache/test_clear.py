from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from pathlib import Path

    from cachy import CacheManager
    from cleo.testers.command_tester import CommandTester

    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory):
    return command_tester_factory("cache clear")


def test_cache_clear_all(
    tester: CommandTester,
    repository_one: str,
    repository_cache_dir: Path,
    cache: CacheManager,
):
    tester.execute(f"{repository_one} --all", inputs="yes")

    assert tester.io.fetch_output() == ""
    # ensure directory is empty
    assert not any((repository_cache_dir / repository_one).iterdir())
    assert not cache.has("cachy:0.1")
    assert not cache.has("cleo:0.2")


def test_cache_clear_all_no(
    tester: CommandTester,
    repository_one: str,
    repository_cache_dir: Path,
    cache: CacheManager,
):
    tester.execute(f"{repository_one} --all", inputs="no")

    assert tester.io.fetch_output() == ""
    # ensure directory is not empty
    assert any((repository_cache_dir / repository_one).iterdir())
    assert cache.has("cachy:0.1")
    assert cache.has("cleo:0.2")


def test_cache_clear_pkg(
    tester: CommandTester,
    repository_one: str,
    cache: CacheManager,
):
    tester.execute(f"{repository_one}:cachy:0.1", inputs="yes")

    assert tester.io.fetch_output() == ""
    assert not cache.has("cachy:0.1")
    assert cache.has("cleo:0.2")


def test_cache_clear_pkg_no(
    tester: CommandTester,
    repository_one: str,
    cache: CacheManager,
):
    tester.execute(f"{repository_one}:cachy:0.1", inputs="no")

    assert tester.io.fetch_output() == ""
    assert cache.has("cachy:0.1")
    assert cache.has("cleo:0.2")
