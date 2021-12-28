from typing import TYPE_CHECKING
from typing import List

import dataclasses
import pytest

from poetry.config.source import Source


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.config.config import Config
    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(
    command_tester_factory: "CommandTesterFactory", poetry_with_source: "Poetry"
) -> "CommandTester":
    return command_tester_factory("source add", poetry=poetry_with_source)


def assert_source_added(
    tester: "CommandTester",
    poetry: "Poetry",
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
    tester: "CommandTester",
    source_existing: Source,
    source_one: Source,
    poetry_with_source: "Poetry",
):
    tester.execute(f"{source_one.name} {source_one.url}")
    assert_source_added(tester, poetry_with_source, source_existing, source_one)


def test_source_add_default(
    tester: "CommandTester",
    source_existing: Source,
    source_default: Source,
    poetry_with_source: "Poetry",
):
    tester.execute(f"--default {source_default.name} {source_default.url}")
    assert_source_added(tester, poetry_with_source, source_existing, source_default)


def test_source_add_secondary(
    tester: "CommandTester",
    source_existing: Source,
    source_secondary: Source,
    poetry_with_source: "Poetry",
):
    tester.execute(f"--secondary {source_secondary.name} {source_secondary.url}")
    assert_source_added(tester, poetry_with_source, source_existing, source_secondary)


def test_source_add_error_default_and_secondary(tester: "CommandTester"):
    tester.execute("--default --secondary error https://error.com")
    assert (
        tester.io.fetch_error().strip()
        == "Cannot configure a source as both default and secondary."
    )
    assert tester.status_code == 1


@pytest.mark.parametrize("is_global", (True, False))
def test_source_add_error_pypi(is_global: bool, tester: "CommandTester"):
    args = "pypi https://test.pypi.org/simple/"
    if is_global:
        args = f"-g {args}"
    tester.execute(args)
    assert (
        tester.io.fetch_error().strip()
        == "Failed to validate addition of pypi: The name [pypi] is reserved for"
        " repositories"
    )
    assert tester.status_code == 1


def test_source_add_existing(
    tester: "CommandTester", source_existing: Source, poetry_with_source: "Poetry"
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


def get_global_sources(poetry: "Poetry") -> List[Source]:
    sources = poetry.config.get("sources", {})
    return [Source(name=name, **source) for name, source in sources.items()]


def assert_global_source_added(
    tester: "CommandTester",
    poetry: "Poetry",
    source_existing: Source,
    source_added: Source,
):
    assert (
        tester.io.fetch_output().strip()
        == f"Adding source with name {source_added.name}."
    )
    assert get_global_sources(poetry) == [source_existing, source_added]
    assert tester.status_code == 0


def test_source_add_global_simple(
    tester: "CommandTester",
    config_with_source: "Config",
    poetry: "Poetry",
    source_one: Source,
    source_existing_global: Source,
):
    tester.execute(f"-g {source_one.name} {source_one.url}")
    assert_global_source_added(tester, poetry, source_existing_global, source_one)


def test_source_add_global_default(
    tester: "CommandTester",
    config_with_source: "Config",
    poetry: "Poetry",
    source_default: Source,
    source_existing_global: Source,
):
    # attempt to add local default
    tester.execute(f"-g -d {source_default.name} {source_default.url}")
    assert_global_source_added(tester, poetry, source_existing_global, source_default)


def test_source_add_global_secondary(
    tester: "CommandTester",
    config_with_source: "Config",
    poetry: "Poetry",
    source_secondary: Source,
    source_existing_global: Source,
):
    tester.execute(f"-g -s {source_secondary.name} {source_secondary.url}")
    assert_global_source_added(tester, poetry, source_existing_global, source_secondary)


def test_source_add_global_existing(
    tester: "CommandTester",
    source_existing_global: Source,
    poetry: "Poetry",
    config_with_source: "Config",
):
    tester.execute(
        f"--default --global {source_existing_global.name} {source_existing_global.url}"
    )
    assert (
        tester.io.fetch_output().strip()
        == f"Source with name {source_existing_global.name} already exists. Updating."
    )
    sources = get_global_sources(poetry)
    assert len(sources) == 1
    assert sources[0] != source_existing_global
    assert sources[0] == dataclasses.replace(source_existing_global, default=True)
