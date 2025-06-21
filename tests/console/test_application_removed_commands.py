from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cleo.testers.application_tester import ApplicationTester

from poetry.console.application import COMMAND_NOT_FOUND_PREFIX_MESSAGE
from poetry.console.application import Application


if TYPE_CHECKING:
    from tests.types import CommandFactory


@pytest.fixture
def tester() -> ApplicationTester:
    return ApplicationTester(Application())


def test_application_removed_command_default_message(
    tester: ApplicationTester,
) -> None:
    tester.execute("nonexistent")
    assert tester.status_code != 0

    stderr = tester.io.fetch_error()
    assert COMMAND_NOT_FOUND_PREFIX_MESSAGE not in stderr
    assert "The requested command nonexistent does not exist." in stderr


@pytest.mark.parametrize(
    ("command", "message"),
    [
        ("shell", "shell command is not installed by default"),
    ],
)
def test_application_removed_command_messages(
    command: str,
    message: str,
    tester: ApplicationTester,
    command_factory: CommandFactory,
) -> None:
    # ensure precondition is met
    assert not tester.application.has(command)

    # verify that the custom message is returned and command fails
    tester.execute(command)
    assert tester.status_code != 0

    stderr = tester.io.fetch_error()
    assert COMMAND_NOT_FOUND_PREFIX_MESSAGE in stderr
    assert message in stderr

    # flush any output/error messages to ensure consistency
    tester.io.clear()

    # add a mock command and verify the command succeeds and no error message is provided
    message = "The shell command was called"
    tester.application.add(command_factory(command, command_handler=message))
    assert tester.application.has(command)

    tester.execute(command)
    assert tester.status_code == 0

    stdout = tester.io.fetch_output()
    stderr = tester.io.fetch_error()
    assert message in stdout
    assert COMMAND_NOT_FOUND_PREFIX_MESSAGE not in stderr
    assert stderr == ""
