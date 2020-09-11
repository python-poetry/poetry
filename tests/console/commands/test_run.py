import pytest
from cleo.testers import CommandTester


def test_run_passes_all_args(app, mocker, env):
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=env)

    command = app.find("run")
    tester = CommandTester(command)

    tester.execute("python -V")

    assert [["python", "-V"]] == env.executed


@pytest.mark.parametrize("project_directory", ["project_with_scripts"])
def test_run_script_relays_exit_code(app):
    command = app.find("run")
    tester = CommandTester(command)
    tester.execute("relay 2", verbosity=True)

    print(tester.io.fetch_output())  # why is it empty?
    assert tester.status_code == 2
