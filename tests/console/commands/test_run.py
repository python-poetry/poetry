from cleo.testers import CommandTester

from poetry.utils._compat import Path
from poetry.utils.env import MockEnv


def test_run_passes_all_args(app, mocker):
    env = MockEnv(path=Path("/prefix"), base=Path("/base/prefix"), is_venv=True)
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=env)

    command = app.find("run")
    tester = CommandTester(command)

    tester.execute("python -V")

    assert [["python", "-V"]] == env.executed
