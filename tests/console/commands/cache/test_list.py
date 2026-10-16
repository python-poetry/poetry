from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.testers.command_tester import CommandTester

    from poetry.utils.cache import FileCache
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("cache list")


def test_cache_list(
    tester: CommandTester,
    caches: list[FileCache[dict[str, str]]],
    repositories: list[str],
) -> None:
    tester.execute()

    expected = f"""\
{repositories[0]}
{repositories[1]}
"""

    assert tester.io.fetch_output() == expected


def test_cache_list_empty(tester: CommandTester, repository_cache_dir: Path) -> None:
    tester.execute()

    expected = """\
No caches found
"""

    assert tester.io.fetch_error() == expected


@pytest.mark.parametrize("filename", [".DS_Store", "README.txt"])
def test_cache_list_ignores_files(
    tester: CommandTester,
    repository_cache_dir: Path,
    caches: list[FileCache[dict[str, str]]],
    repositories: list[str],
    filename: str,
) -> None:
    (repository_cache_dir / filename).touch()

    tester.execute()

    assert tester.io.fetch_output() == "".join(f"{name}\n" for name in repositories)
    assert tester.io.fetch_error() == ""
    assert tester.status_code == 0


@pytest.mark.parametrize("filename", [".DS_Store", "README.txt"])
def test_cache_list_only_files(
    tester: CommandTester, repository_cache_dir: Path, filename: str
) -> None:
    repository_cache_dir.mkdir(parents=True)
    (repository_cache_dir / filename).touch()

    tester.execute()

    assert tester.io.fetch_output() == ""
    assert tester.io.fetch_error() == "No caches found\n"
    assert tester.status_code == 0
