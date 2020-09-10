import pytest


@pytest.fixture
def tester(command_tester_factory):
    return command_tester_factory("run")


@pytest.fixture(autouse=True)
def patches(mocker, env):
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=env)


def test_run_passes_all_args(tester, env):
    tester.execute("python -V")
    assert [["python", "-V"]] == env.executed
