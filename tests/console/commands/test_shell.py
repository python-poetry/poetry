from __future__ import annotations

import sys

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.utils.env import MockEnv
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("shell")


def test_shell_active_venv_deactivated(
    tester: CommandTester, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("POETRY_ACTIVE", "1")
    tester.execute("")
    out = tester.io.fetch_output().strip()
    assert (
        out
        == "Poetry shell is active but venv is deactivated. Exit shell and re-launch."
    )


def test_shell_active_venv_activated(
    tester: CommandTester, monkeypatch: MonkeyPatch, env: MockEnv
) -> None:
    monkeypatch.setenv("POETRY_ACTIVE", "1")
    monkeypatch.setattr(sys, "prefix", str(env.path))
    tester.execute("")
    out = tester.io.fetch_output().strip()
    assert out == f"Virtual environment already activated: {env.path}"


def test_shell_activate(
    tester: CommandTester, mocker: MockerFixture, env: MockEnv
) -> None:
    mock = mocker.patch("poetry.utils.shell.Shell.activate")
    tester.execute("")
    mock.assert_called_with(env)
