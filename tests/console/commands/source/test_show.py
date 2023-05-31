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


@pytest.fixture
def tester_no_sources(
    command_tester_factory: CommandTesterFactory,
    poetry_without_source: Poetry,
) -> CommandTester:
    return command_tester_factory("source show", poetry=poetry_without_source)


@pytest.fixture
def tester_pypi(
    command_tester_factory: CommandTesterFactory,
    poetry_with_pypi: Poetry,
) -> CommandTester:
    return command_tester_factory("source show", poetry=poetry_with_pypi)


@pytest.fixture
def tester_pypi_and_other(
    command_tester_factory: CommandTesterFactory,
    poetry_with_pypi_and_other: Poetry,
) -> CommandTester:
    return command_tester_factory("source show", poetry=poetry_with_pypi_and_other)


@pytest.fixture
def tester_all_types(
    command_tester_factory: CommandTesterFactory,
    poetry_with_source: Poetry,
    add_all_source_types: None,
) -> CommandTester:
    return command_tester_factory("source show", poetry=poetry_with_source)


def test_source_show_simple(tester: CommandTester) -> None:
    tester.execute("")

    expected = """\
name      : existing
url       : https://existing.com
priority  : primary

name      : one
url       : https://one.com
priority  : primary

name      : two
url       : https://two.com
priority  : primary
""".splitlines()
    assert [
        line.strip() for line in tester.io.fetch_output().strip().splitlines()
    ] == expected
    assert tester.status_code == 0


@pytest.mark.parametrize("modifier", ["lower", "upper"])
def test_source_show_one(
    tester: CommandTester, source_one: Source, modifier: str
) -> None:
    tester.execute(getattr(f"{source_one.name}", modifier)())

    expected = """\
name      : one
url       : https://one.com
priority  : primary
""".splitlines()
    assert [
        line.strip() for line in tester.io.fetch_output().strip().splitlines()
    ] == expected
    assert tester.status_code == 0


@pytest.mark.parametrize("modifier", ["lower", "upper"])
def test_source_show_two(
    tester: CommandTester, source_one: Source, source_two: Source, modifier: str
) -> None:
    tester.execute(getattr(f"{source_one.name} {source_two.name}", modifier)())

    expected = """\
name      : one
url       : https://one.com
priority  : primary

name      : two
url       : https://two.com
priority  : primary
""".splitlines()
    assert [
        line.strip() for line in tester.io.fetch_output().strip().splitlines()
    ] == expected
    assert tester.status_code == 0


@pytest.mark.parametrize(
    "source_str",
    (
        "source_primary",
        "source_default",
        "source_secondary",
        "source_supplemental",
        "source_explicit",
    ),
)
def test_source_show_given_priority(
    tester_all_types: CommandTester, source_str: str, request: pytest.FixtureRequest
) -> None:
    source = request.getfixturevalue(source_str)
    tester_all_types.execute(f"{source.name}")

    expected = f"""\
name      : {source.name}
url       : {source.url}
priority  : {source.name}
""".splitlines()
    assert [
        line.strip() for line in tester_all_types.io.fetch_output().strip().splitlines()
    ] == expected
    assert tester_all_types.status_code == 0


def test_source_show_pypi(tester_pypi: CommandTester) -> None:
    tester_pypi.execute("")
    expected = """\
name      : PyPI
priority  : primary
""".splitlines()
    assert [
        line.strip() for line in tester_pypi.io.fetch_output().strip().splitlines()
    ] == expected
    assert tester_pypi.status_code == 0


def test_source_show_pypi_and_other(tester_pypi_and_other: CommandTester) -> None:
    tester_pypi_and_other.execute("")
    expected = """\
name      : existing
url       : https://existing.com
priority  : primary

name      : PyPI
priority  : primary
""".splitlines()
    assert [
        line.strip()
        for line in tester_pypi_and_other.io.fetch_output().strip().splitlines()
    ] == expected
    assert tester_pypi_and_other.status_code == 0


def test_source_show_no_sources(tester_no_sources: CommandTester) -> None:
    tester_no_sources.execute("error")
    assert (
        tester_no_sources.io.fetch_output().strip()
        == "No sources configured for this project."
    )
    assert tester_no_sources.status_code == 0


def test_source_show_error(tester: CommandTester) -> None:
    tester.execute("error")
    assert tester.io.fetch_error().strip() == "No source found with name(s): error"
    assert tester.status_code == 1
