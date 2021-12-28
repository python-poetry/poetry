from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.config.config import Config
    from poetry.config.source import Source
    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(
    command_tester_factory: "CommandTesterFactory",
    poetry_with_source: "Poetry",
    add_multiple_sources: None,
) -> "CommandTester":
    return command_tester_factory("source remove", poetry=poetry_with_source)


def test_source_remove_simple(
    tester: "CommandTester",
    poetry_with_source: "Poetry",
    source_existing: "Source",
    source_one: "Source",
    source_two: "Source",
):
    tester.execute(f"{source_existing.name}")
    assert (
        tester.io.fetch_output().strip()
        == f"Removing source with name {source_existing.name}."
    )

    poetry_with_source.pyproject.reload()
    sources = poetry_with_source.get_sources()
    assert sources == [source_one, source_two]

    assert tester.status_code == 0


@pytest.mark.parametrize("is_global", [True, False])
def test_source_remove_error(is_global: bool, tester: "CommandTester"):
    args = "error"
    if is_global:
        args = f"-g {args}"
    tester.execute(args)
    assert tester.io.fetch_error().strip() == "Source with name error was not found."
    assert tester.status_code == 1


def test_source_remove_global(
    tester: "CommandTester",
    config_with_source: "Config",
    source_existing_global: "Source",
    mocker: "MockerFixture",
):
    patch = mocker.patch.object(config_with_source.config_source, "remove_property")
    tester.execute(f"-g {source_existing_global.name}")
    assert tester.status_code == 0
    assert patch.call_args[0] == (f"sources.{source_existing_global.name}",)
