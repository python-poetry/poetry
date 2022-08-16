from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.config.source import Source
    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(
    command_tester_factory: CommandTesterFactory,
    poetry_with_source: Poetry,
    add_multiple_sources: None,
) -> CommandTester:
    return command_tester_factory("source show", poetry=poetry_with_source)


def test_source_show_simple(tester: CommandTester):
    tester.execute("")

    expected = """\
name       : existing
url        : https://existing.com
default    : no
secondary  : no

name       : one
url        : https://one.com
default    : no
secondary  : no

name       : two
url        : https://two.com
default    : no
secondary  : no
""".splitlines()
    assert [
        line.strip() for line in tester.io.fetch_output().strip().splitlines()
    ] == expected
    assert tester.status_code == 0


def test_source_show_one(tester: CommandTester, source_one: Source):
    tester.execute(f"{source_one.name}")

    expected = """\
name       : one
url        : https://one.com
default    : no
secondary  : no
""".splitlines()
    assert [
        line.strip() for line in tester.io.fetch_output().strip().splitlines()
    ] == expected
    assert tester.status_code == 0


def test_source_show_two(tester: CommandTester, source_one: Source, source_two: Source):
    tester.execute(f"{source_one.name} {source_two.name}")

    expected = """\
name       : one
url        : https://one.com
default    : no
secondary  : no

name       : two
url        : https://two.com
default    : no
secondary  : no
""".splitlines()
    assert [
        line.strip() for line in tester.io.fetch_output().strip().splitlines()
    ] == expected
    assert tester.status_code == 0


def test_source_show_error(tester: CommandTester):
    tester.execute("error")
    assert tester.io.fetch_error().strip() == "No source found with name(s): error"
    assert tester.status_code == 1
