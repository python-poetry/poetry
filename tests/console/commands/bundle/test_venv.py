from pathlib import Path


def test_venv_calls_venv_bundler(app_tester, mocker):
    mock = mocker.patch(
        "poetry.bundle.venv_bundler.VenvBundler.bundle", side_effect=[True, False]
    )

    app_tester.application.catch_exceptions(False)
    assert 0 == app_tester.execute("bundle venv /foo")
    assert 1 == app_tester.execute("bundle venv /foo --python python3.8 --clear")

    assert [
        mocker.call(
            app_tester.application.poetry,
            mocker.ANY,
            Path("/foo"),
            executable=None,
            remove=False,
        ),
        mocker.call(
            app_tester.application.poetry,
            mocker.ANY,
            Path("/foo"),
            executable="python3.8",
            remove=True,
        ),
    ] == mock.call_args_list
