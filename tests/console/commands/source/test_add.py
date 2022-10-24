from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.config.source import Source
from poetry.repositories.repository_pool import Priority


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(
    command_tester_factory: CommandTesterFactory, poetry_with_source: Poetry
) -> CommandTester:
    return command_tester_factory("source add", poetry=poetry_with_source)


def assert_source_added_legacy(
    tester: CommandTester,
    poetry: Poetry,
    source_existing: Source,
    source_added: Source,
) -> None:
    assert (
        tester.io.fetch_error().strip()
        == "Warning: Priority was set through a deprecated flag"
        " (--default or --secondary). Consider using --priority next"
        " time."
    )
    assert (
        tester.io.fetch_output().strip()
        == f"Adding source with name {source_added.name}."
    )
    poetry.pyproject.reload()
    sources = poetry.get_sources()
    assert sources == [source_existing, source_added]
    assert tester.status_code == 0


def assert_source_added(
    tester: CommandTester,
    poetry: Poetry,
    source_existing: Source,
    source_added: Source,
) -> None:
    assert (
        tester.io.fetch_output().strip()
        == f"Adding source with name {source_added.name}."
    )
    poetry.pyproject.reload()
    sources = poetry.get_sources()
    assert sources == [source_existing, source_added]
    assert tester.status_code == 0


def test_source_add_simple(
    tester: CommandTester,
    source_existing: Source,
    source_one: Source,
    poetry_with_source: Poetry,
) -> None:
    tester.execute(f"{source_one.name} {source_one.url}")
    assert_source_added(tester, poetry_with_source, source_existing, source_one)


def test_source_add_default_legacy(
    tester: CommandTester,
    source_existing: Source,
    source_default: Source,
    poetry_with_source: Poetry,
) -> None:
    tester.execute(f"--default {source_default.name} {source_default.url}")
    assert_source_added_legacy(
        tester, poetry_with_source, source_existing, source_default
    )


def test_source_add_secondary_legacy(
    tester: CommandTester,
    source_existing: Source,
    source_secondary: Source,
    poetry_with_source: Poetry,
):
    tester.execute(f"--secondary {source_secondary.name} {source_secondary.url}")
    assert_source_added_legacy(
        tester, poetry_with_source, source_existing, source_secondary
    )


def test_source_add_default(
    tester: CommandTester,
    source_existing: Source,
    source_default: Source,
    poetry_with_source: Poetry,
):
    tester.execute(f"--priority=default {source_default.name} {source_default.url}")
    assert_source_added(tester, poetry_with_source, source_existing, source_default)


def test_source_add_second_default_fails(
    tester: CommandTester,
    source_existing: Source,
    source_default: Source,
    poetry_with_source: Poetry,
):
    tester.execute(f"--priority=default {source_default.name} {source_default.url}")
    assert_source_added(tester, poetry_with_source, source_existing, source_default)
    poetry_with_source.pyproject.reload()

    tester.execute(f"--priority=default {source_default.name}1 {source_default.url}")
    assert (
        tester.io.fetch_error().strip()
        == f"Source with name {source_default.name} is already set to"
        " default. Only one default source can be configured at a"
        " time."
    )
    assert tester.status_code == 1


def test_source_add_secondary(
    tester: CommandTester,
    source_existing: Source,
    source_secondary: Source,
    poetry_with_source: Poetry,
) -> None:
    tester.execute(
        f"--priority=secondary {source_secondary.name} {source_secondary.url}"
    )
    assert_source_added(tester, poetry_with_source, source_existing, source_secondary)


def test_source_add_explicit(
    tester: CommandTester,
    source_existing: Source,
    source_explicit: Source,
    poetry_with_source: Poetry,
) -> None:
    tester.execute(f"--priority=explicit {source_explicit.name} {source_explicit.url}")
    assert_source_added(tester, poetry_with_source, source_existing, source_explicit)


def test_source_add_error_default_and_secondary_legacy(tester: CommandTester) -> None:
    tester.execute("--default --secondary error https://error.com")
    assert (
        tester.io.fetch_error().strip()
        == "Cannot configure a source as both default and secondary."
    )
    assert tester.status_code == 1


def test_source_add_error_priority_and_deprecated_legacy(tester: CommandTester):
    tester.execute("--priority secondary --secondary error https://error.com")
    assert (
        tester.io.fetch_error().strip()
        == "Priority was passed through both --priority and a"
        " deprecated flag (--default or --secondary). Please only provide"
        " one of these."
    )
    assert tester.status_code == 1


def test_source_add_error_pypi(tester: CommandTester) -> None:
    tester.execute("pypi https://test.pypi.org/simple/")
    assert (
        tester.io.fetch_error().strip()
        == "Failed to validate addition of pypi: The name [pypi] is reserved for"
        " repositories"
    )
    assert tester.status_code == 1


def test_source_add_existing_legacy(
    tester: CommandTester, source_existing: Source, poetry_with_source: Poetry
) -> None:
    tester.execute(f"--default {source_existing.name} {source_existing.url}")
    assert (
        tester.io.fetch_error().strip()
        == "Warning: Priority was set through a deprecated flag"
        " (--default or --secondary). Consider using --priority next"
        " time."
    )
    assert (
        tester.io.fetch_output().strip()
        == f"Source with name {source_existing.name} already exists. Updating."
    )

    poetry_with_source.pyproject.reload()
    sources = poetry_with_source.get_sources()

    assert len(sources) == 1
    assert sources[0] != source_existing
    expected_source = Source(
        name=source_existing.name, url=source_existing.url, priority=Priority.DEFAULT
    )
    assert sources[0] == expected_source


def test_source_add_existing_no_change(
    tester: CommandTester, source_existing: Source, poetry_with_source: Poetry
):
    tester.execute(f"--priority=primary {source_existing.name} {source_existing.url}")
    assert (
        tester.io.fetch_output().strip()
        == f"Source with name {source_existing.name} already exists. Skipping addition."
    )

    poetry_with_source.pyproject.reload()
    sources = poetry_with_source.get_sources()

    assert len(sources) == 1
    assert sources[0] == source_existing


def test_source_add_existing_updating(
    tester: CommandTester, source_existing: Source, poetry_with_source: Poetry
):
    tester.execute(f"--priority=default {source_existing.name} {source_existing.url}")
    assert (
        tester.io.fetch_output().strip()
        == f"Source with name {source_existing.name} already exists. Updating."
    )

    poetry_with_source.pyproject.reload()
    sources = poetry_with_source.get_sources()

    assert len(sources) == 1
    assert sources[0] != source_existing
    expected_source = Source(
        name=source_existing.name, url=source_existing.url, priority=Priority.DEFAULT
    )
    assert sources[0] == expected_source


def test_source_add_existing_fails_due_to_other_default(
    tester: CommandTester,
    source_existing: Source,
    source_default: Source,
    poetry_with_source: Poetry,
):
    tester.execute(f"--priority=default {source_default.name} {source_default.url}")
    tester.io.fetch_output()

    tester.execute(f"--priority=default {source_existing.name} {source_existing.url}")

    assert (
        tester.io.fetch_error().strip()
        == f"Source with name {source_default.name} is already set to"
        " default. Only one default source can be configured at a"
        " time."
    )
    assert tester.io.fetch_output().strip() == ""
    assert tester.status_code == 1
