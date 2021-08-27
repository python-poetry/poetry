<<<<<<< HEAD
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.config.source import Source
    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(
    command_tester_factory: "CommandTesterFactory",
    poetry_with_source: "Poetry",
    add_multiple_sources: None,
) -> "CommandTester":
=======
import pytest


@pytest.fixture
def tester(command_tester_factory, poetry_with_source, add_multiple_sources):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return command_tester_factory("source remove", poetry=poetry_with_source)


def test_source_remove_simple(
<<<<<<< HEAD
    tester: "CommandTester",
    poetry_with_source: "Poetry",
    source_existing: "Source",
    source_one: "Source",
    source_two: "Source",
=======
    tester, poetry_with_source, source_existing, source_one, source_two
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_source_remove_error(tester: "CommandTester"):
=======
def test_source_remove_error(tester):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute("error")
    assert tester.io.fetch_error().strip() == "Source with name error was not found."
    assert tester.status_code == 1
