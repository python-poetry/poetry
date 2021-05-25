import pytest


@pytest.fixture
def tester(command_tester_factory):
    return command_tester_factory("run")


@pytest.fixture(autouse=True)
def patches(mocker, env):
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=env)


def test_run_passes_all_args(app_tester, env):
    app_tester.execute("run python -V")
    assert [["python", "-V"]] == env.executed


def test_run_keeps_options_passed_before_command(app_tester, env):
    app_tester.execute("-V --no-ansi run python", decorated=True)

    assert not app_tester.io.is_decorated()
    assert app_tester.io.fetch_output() == app_tester.io.remove_format(
        app_tester.application.long_version + "\n"
    )
    assert [] == env.executed
