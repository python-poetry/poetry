from __future__ import annotations

import os

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("shell")


def test_shell(tester: CommandTester, mocker: MockerFixture):
    shell_activate = mocker.patch("poetry.utils.shell.Shell.activate")

    tester.execute()

    expected_output = f"Spawning shell within {tester.command.env.path}\n"

    shell_activate.assert_called_once_with(tester.command.env)
    assert tester.io.fetch_output() == expected_output
    assert tester.status_code == 0


def test_shell_already_active(tester: CommandTester, mocker: MockerFixture):
    os.environ["POETRY_ACTIVE"] = "1"
    shell_activate = mocker.patch("poetry.utils.shell.Shell.activate")

    tester.execute()

    expected_output = (
        f"Virtual environment already activated: {tester.command.env.path}\n"
    )

    shell_activate.assert_not_called()
    assert tester.io.fetch_output() == expected_output
    assert tester.status_code == 0
