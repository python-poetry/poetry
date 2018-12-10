import os
import shutil
import sys

import tomlkit

from cleo.testers import CommandTester

from poetry.semver import Version
from poetry.utils._compat import Path
from poetry.utils.env import EnvManager
from poetry.utils.env import MockEnv
from poetry.utils.toml_file import TomlFile


CWD = Path(__file__).parent.parent / "fixtures" / "simple_project"


def build_venv(path, executable=None):
    os.mkdir(path)


def remove_venv(path):
    shutil.rmtree(path)


def check_output_wrapper(version=Version.parse("3.7.1")):
    def check_output(cmd, *args, **kwargs):
        if "sys.version_info[:3]" in cmd:
            return version.text
        elif "sys.version_info[:2]" in cmd:
            return "{}.{}".format(version.major, version.minor)
        else:
            return str(Path("/prefix"))

    return check_output


def test_activate_activates_non_existing_virtualenv_no_envs_file(
    app, tmp_dir, config, mocker
):
    app.poetry._config = config

    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch("subprocess.check_output", side_effect=check_output_wrapper())
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None), ("/prefix", None)],
    )
    m = mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    command = app.find("env use")
    tester = CommandTester(command)
    tester.execute("3.7")

    venv_name = EnvManager.generate_env_name(
        "simple_project", str(app.poetry.file.parent)
    )

    m.assert_called_with(
        os.path.join(tmp_dir, "{}-py3.7".format(venv_name)), executable="python3.7"
    )

    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

    expected = """\
Creating virtualenv {} in {}
Using virtualenv: {}
""".format(
        "{}-py3.7".format(venv_name),
        tmp_dir,
        os.path.join(tmp_dir, "{}-py3.7".format(venv_name)),
    )

    assert expected == tester.io.fetch_output()


def test_get_prefers_explicitly_activated_virtualenvs_over_env_var(
    app, tmp_dir, config, mocker
):
    app.poetry._config = config

    os.environ["VIRTUAL_ENV"] = "/environment/prefix"

    venv_name = EnvManager.generate_env_name(
        "simple_project", str(app.poetry.file.parent)
    )
    current_python = sys.version_info[:3]
    python_minor = ".".join(str(v) for v in current_python[:2])
    python_patch = ".".join(str(v) for v in current_python)

    config.add_property("settings.virtualenvs.path", str(tmp_dir))
    (Path(tmp_dir) / "{}-py{}".format(venv_name, python_minor)).mkdir()

    envs_file = TomlFile(Path(tmp_dir) / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": python_minor, "patch": python_patch}
    envs_file.write(doc)

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version(*current_python)),
    )
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None), ("/prefix", None), ("/prefix", None)],
    )

    command = app.find("env use")
    tester = CommandTester(command)
    tester.execute(python_minor)

    expected = """\
Using virtualenv: {}
""".format(
        os.path.join(tmp_dir, "{}-py{}".format(venv_name, python_minor))
    )

    assert expected == tester.io.fetch_output()


def test_get_prefers_explicitly_activated_non_existing_virtualenvs_over_env_var(
    app, tmp_dir, config, mocker
):
    app.poetry._config = config

    os.environ["VIRTUAL_ENV"] = "/environment/prefix"

    venv_name = EnvManager.generate_env_name(
        "simple_project", str(app.poetry.file.parent)
    )
    current_python = sys.version_info[:3]
    python_minor = ".".join(str(v) for v in current_python[:2])

    config.add_property("settings.virtualenvs.path", str(tmp_dir))

    mocker.patch(
        "poetry.utils.env.EnvManager._env",
        new_callable=mocker.PropertyMock,
        return_value=MockEnv(
            path=Path("/environment/prefix"),
            base=Path("/base/prefix"),
            version_info=current_python,
            is_venv=True,
        ),
    )

    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version(*current_python)),
    )
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None), ("/prefix", None), ("/prefix", None)],
    )
    mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    command = app.find("env use")
    tester = CommandTester(command)
    tester.execute(python_minor)

    expected = """\
Creating virtualenv {} in {}
Using virtualenv: {}
""".format(
        "{}-py{}".format(venv_name, python_minor),
        tmp_dir,
        os.path.join(tmp_dir, "{}-py{}".format(venv_name, python_minor)),
    )

    assert expected == tester.io.fetch_output()
