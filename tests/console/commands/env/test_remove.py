from cleo.testers import CommandTester

from poetry.utils._compat import Path
from poetry.utils.env import EnvManager

from .test_use import Version
from .test_use import check_output_wrapper


def test_remove_by_python_version(app, tmp_dir, config, mocker):
    app.poetry._config = config

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    venv_name = EnvManager.generate_env_name(
        "simple_project", str(app.poetry.file.parent)
    )
    (Path(tmp_dir) / "{}-py3.7".format(venv_name)).mkdir()
    (Path(tmp_dir) / "{}-py3.6".format(venv_name)).mkdir()

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    command = app.find("env remove")
    tester = CommandTester(command)
    tester.execute("3.6")

    assert not (Path(tmp_dir) / "{}-py3.6".format(venv_name)).exists()

    expected = "Deleted virtualenv: {}\n".format(
        (Path(tmp_dir) / "{}-py3.6".format(venv_name))
    )

    assert expected == tester.io.fetch_output()


def test_remove_by_name(app, tmp_dir, config, mocker):
    app.poetry._config = config

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    venv_name = EnvManager.generate_env_name(
        "simple_project", str(app.poetry.file.parent)
    )
    (Path(tmp_dir) / "{}-py3.7".format(venv_name)).mkdir()
    (Path(tmp_dir) / "{}-py3.6".format(venv_name)).mkdir()

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    command = app.find("env remove")
    tester = CommandTester(command)
    tester.execute("{}-py3.6".format(venv_name))

    assert not (Path(tmp_dir) / "{}-py3.6".format(venv_name)).exists()

    expected = "Deleted virtualenv: {}\n".format(
        (Path(tmp_dir) / "{}-py3.6".format(venv_name))
    )

    assert expected == tester.io.fetch_output()
