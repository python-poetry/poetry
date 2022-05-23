from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.testers.command_tester import CommandTester

    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("cache list")


def test_cache_list(
    tester: CommandTester, mock_caches: None, repository_one: str, repository_two: str
):
    tester.execute()

    expected = f"""\
{repository_one}
{repository_two}
"""

    assert tester.io.fetch_output() == expected


def test_cache_list_empty(tester: CommandTester, repository_cache_dir: Path):
    tester.execute()

    expected = """\
No caches found
"""

    assert tester.io.fetch_error() == expected
