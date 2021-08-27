from pathlib import Path
<<<<<<< HEAD
from typing import TYPE_CHECKING
=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

import pytest


<<<<<<< HEAD
if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
    return command_tester_factory("check")


def test_check_valid(tester: "CommandTester"):
=======
@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("check")


def test_check_valid(tester):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute()

    expected = """\
All set!
"""

    assert expected == tester.io.fetch_output()


<<<<<<< HEAD
def test_check_invalid(mocker: "MockerFixture", tester: "CommandTester"):
=======
def test_check_invalid(mocker, tester):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.patch(
        "poetry.factory.Factory.locate",
        return_value=Path(__file__).parent.parent.parent
        / "fixtures"
        / "invalid_pyproject"
        / "pyproject.toml",
    )

    tester.execute()

    expected = """\
Error: 'description' is a required property
Warning: A wildcard Python dependency is ambiguous. Consider specifying a more explicit one.
Warning: The "pendulum" dependency specifies the "allows-prereleases" property, which is deprecated. Use "allow-prereleases" instead.
"""

    assert expected == tester.io.fetch_output()
