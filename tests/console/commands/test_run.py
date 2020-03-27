from cleo.testers import CommandTester


def test_run_passes_all_args(app, mocker, env):
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=env)

    command = app.find("run")
    tester = CommandTester(command)

    tester.execute("python -V")

    assert [["python", "-V"]] == env.executed
