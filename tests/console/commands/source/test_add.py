from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.config.source import Source
from poetry.repositories.repository_pool import Priority


if TYPE_CHECKING:
    from collections.abc import Iterable

    from cleo.testers.command_tester import CommandTester

    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(
    command_tester_factory: CommandTesterFactory, poetry_with_source: Poetry
) -> CommandTester:
    return command_tester_factory("source add", poetry=poetry_with_source)


def assert_source_added(
    tester: CommandTester,
    poetry: Poetry,
    added_source: Source,
    existing_sources: Iterable[Source] = (),
) -> None:
    assert tester.io.fetch_error().strip() == ""
    assert (
        tester.io.fetch_output().strip()
        == f"Adding source with name {added_source.name}."
    )
    poetry.pyproject.reload()
    sources = poetry.get_sources()
    assert sources == [*existing_sources, added_source]
    assert tester.status_code == 0


def test_source_add_simple(
    tester: CommandTester,
    source_existing: Source,
    source_one: Source,
    poetry_with_source: Poetry,
) -> None:
    tester.execute(f"{source_one.name} {source_one.url}")
    assert_source_added(tester, poetry_with_source, source_one, [source_existing])


def test_source_add_simple_without_existing_sources(
    tester: CommandTester,
    source_one: Source,
    poetry_without_source: Poetry,
) -> None:
    tester.execute(f"{source_one.name} {source_one.url}")
    assert_source_added(tester, poetry_without_source, source_one)


def test_source_add_simple_without_existing_poetry_section(
    tester: CommandTester,
    source_one: Source,
    poetry_without_poetry_section: Poetry,
) -> None:
    tester.execute(f"{source_one.name} {source_one.url}")
    assert_source_added(tester, poetry_without_poetry_section, source_one)


def test_source_add_supplemental(
    tester: CommandTester,
    source_existing: Source,
    source_supplemental: Source,
    poetry_with_source: Poetry,
) -> None:
    tester.execute(
        f"--priority=supplemental {source_supplemental.name} {source_supplemental.url}"
    )
    assert_source_added(
        tester, poetry_with_source, source_supplemental, [source_existing]
    )


def test_source_add_explicit(
    tester: CommandTester,
    source_existing: Source,
    source_explicit: Source,
    poetry_with_source: Poetry,
) -> None:
    tester.execute(f"--priority=explicit {source_explicit.name} {source_explicit.url}")
    assert_source_added(tester, poetry_with_source, source_explicit, [source_existing])


def test_source_add_error_no_url(tester: CommandTester) -> None:
    tester.execute("foo")
    assert (
        tester.io.fetch_error().strip()
        == "A custom source cannot be added without a URL."
    )
    assert tester.status_code == 1


def test_source_add_error_pypi(tester: CommandTester) -> None:
    tester.execute("pypi https://test.pypi.org/simple/")
    assert (
        tester.io.fetch_error().strip() == "The URL of PyPI is fixed and cannot be set."
    )
    assert tester.status_code == 1


@pytest.mark.parametrize("name", ["pypi", "PyPI"])
def test_source_add_pypi(
    name: str,
    tester: CommandTester,
    source_existing: Source,
    source_pypi: Source,
    poetry_with_source: Poetry,
) -> None:
    tester.execute(name)
    assert_source_added(tester, poetry_with_source, source_pypi, [source_existing])


def test_source_add_pypi_explicit(
    tester: CommandTester,
    source_existing: Source,
    source_pypi_explicit: Source,
    poetry_with_source: Poetry,
) -> None:
    tester.execute("--priority=explicit PyPI")
    assert_source_added(
        tester, poetry_with_source, source_pypi_explicit, [source_existing]
    )


@pytest.mark.parametrize("modifier", ["lower", "upper"])
def test_source_add_existing_no_change_except_case_of_name(
    modifier: str,
    tester: CommandTester,
    source_existing: Source,
    poetry_with_source: Poetry,
) -> None:
    name = getattr(source_existing.name, modifier)()
    tester.execute(f"--priority=primary {name} {source_existing.url}")
    assert (
        tester.io.fetch_output().strip()
        == f"Source with name {name} already exists. Updating."
    )

    poetry_with_source.pyproject.reload()
    sources = poetry_with_source.get_sources()

    assert len(sources) == 1
    assert sources[0].name == getattr(source_existing.name, modifier)()
    assert sources[0].url == source_existing.url
    assert sources[0].priority == source_existing.priority


@pytest.mark.parametrize("modifier", ["lower", "upper"])
def test_source_add_existing_updating(
    modifier: str,
    tester: CommandTester,
    source_existing: Source,
    poetry_with_source: Poetry,
) -> None:
    name = getattr(source_existing.name, modifier)()
    tester.execute(f"--priority=supplemental {name} {source_existing.url}")
    assert (
        tester.io.fetch_output().strip()
        == f"Source with name {name} already exists. Updating."
    )

    poetry_with_source.pyproject.reload()
    sources = poetry_with_source.get_sources()

    assert len(sources) == 1
    assert sources[0] != source_existing
    expected_source = Source(
        name=name, url=source_existing.url, priority=Priority.SUPPLEMENTAL
    )
    assert sources[0] == expected_source
