<<<<<<< HEAD
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.application_tester import ApplicationTester
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.utils.env import MockEnv
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
=======
import pytest


@pytest.fixture
def tester(command_tester_factory):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return command_tester_factory("run")


@pytest.fixture(autouse=True)
<<<<<<< HEAD
def patches(mocker: "MockerFixture", env: "MockEnv") -> None:
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=env)


def test_run_passes_all_args(app_tester: "ApplicationTester", env: "MockEnv"):
=======
def patches(mocker, env):
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=env)


def test_run_passes_all_args(app_tester, env):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    app_tester.execute("run python -V")
    assert [["python", "-V"]] == env.executed


<<<<<<< HEAD
def test_run_keeps_options_passed_before_command(
    app_tester: "ApplicationTester", env: "MockEnv"
):
=======
def test_run_keeps_options_passed_before_command(app_tester, env):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    app_tester.execute("-V --no-ansi run python", decorated=True)

    assert not app_tester.io.is_decorated()
    assert app_tester.io.fetch_output() == app_tester.io.remove_format(
        app_tester.application.long_version + "\n"
    )
    assert [] == env.executed
