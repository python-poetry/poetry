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
    return command_tester_factory("run")


@pytest.fixture(autouse=True)
def patches(mocker: "MockerFixture", env: "MockEnv") -> None:
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=env)


def test_run_passes_all_args(app_tester: "ApplicationTester", env: "MockEnv"):
    app_tester.execute("run python -V")
    assert [["python", "-V"]] == env.executed
    
def test_run_fails_no_args(app_tester: "ApplicationTester", env: "MockEnv"):
    with pytest.raises(ValueError) as e:
        app_tester.execute("run")
    
    assert str(e.value) == "Missing arguments; try `poetry run python your_script.py`"



def test_run_keeps_options_passed_before_command(
    app_tester: "ApplicationTester", env: "MockEnv"
):
    app_tester.execute("-V --no-ansi run python", decorated=True)

    assert not app_tester.io.is_decorated()
    assert app_tester.io.fetch_output() == app_tester.io.remove_format(
        app_tester.application.long_version + "\n"
    )
    assert [] == env.executed
