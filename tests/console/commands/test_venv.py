from cleo.testers import CommandTester

from poetry.utils.env import MockEnv


def test_venv_prints_path(app, mocker):
    venv_path = '/path/to/cache_dir/pypoetry/virtualenvs/myproj-3.6'
    mock_env = MockEnv()
    mock_env._path = venv_path
    mocker.patch("poetry.utils.env.Env.get", return_value=mock_env)

    command = app.find("venv")
    tester = CommandTester(command)
    tester.execute([("command", command.get_name())])

    assert tester.get_display(True).strip() == venv_path
