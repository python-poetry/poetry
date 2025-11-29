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
