from __future__ import annotations

import dataclasses

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.config.source import Source
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
):
    tester.execute(f"{source_one.name} {source_one.url}")
    assert_source_added(tester, poetry_with_source, source_existing, source_one)


def test_source_add_default(
    tester: CommandTester,
    source_existing: Source,
    source_default: Source,
    poetry_with_source: Poetry,
):
    tester.execute(f"--default {source_default.name} {source_default.url}")
    assert_source_added(tester, poetry_with_source, source_existing, source_default)


def test_source_add_secondary(
    tester: CommandTester,
    source_existing: Source,
    source_secondary: Source,
    poetry_with_source: Poetry,
):
    tester.execute(f"--secondary {source_secondary.name} {source_secondary.url}")
    assert_source_added(tester, poetry_with_source, source_existing, source_secondary)


def test_source_add_error_default_and_secondary(tester: CommandTester):
    tester.execute("--default --secondary error https://error.com")
    assert (
        tester.io.fetch_error().strip()
        == "Cannot configure a source as both default and secondary."
    )
    assert tester.status_code == 1


def test_source_add_error_pypi(tester: CommandTester):
    tester.execute("pypi https://test.pypi.org/simple/")
    assert (
        tester.io.fetch_error().strip()
        == "Failed to validate addition of pypi: The name [pypi] is reserved for"
        " repositories"
    )
    assert tester.status_code == 1


def test_source_add_existing(
    tester: CommandTester, source_existing: Source, poetry_with_source: Poetry
):
    tester.execute(f"--default {source_existing.name} {source_existing.url}")
    assert (
        tester.io.fetch_output().strip()
        == f"Source with name {source_existing.name} already exists. Updating."
    )

    poetry_with_source.pyproject.reload()
    sources = poetry_with_source.get_sources()

    assert len(sources) == 1
    assert sources[0] != source_existing
    assert sources[0] == dataclasses.replace(source_existing, default=True)
