import os

from pathlib import Path

import pytest
import tomlkit

from poetry.core.semver.version import Version
from poetry.core.toml.file import TOMLFile
from poetry.utils.env import MockEnv
from tests.console.commands.env.helpers import build_venv
from tests.console.commands.env.helpers import check_output_wrapper


@pytest.fixture(autouse=True)
def setup(mocker):
    mocker.stopall()
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]


@pytest.fixture(autouse=True)
def mock_subprocess_calls(setup, current_python, mocker):
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.from_parts(*current_python)),
    )
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None), ("/prefix", None), ("/prefix", None)],
    )


@pytest.fixture
def tester(command_tester_factory):
    return command_tester_factory("env use")


def test_activate_activates_non_existing_virtualenv_no_envs_file(
    mocker, tester, venv_cache, venv_name, venvs_in_cache_config
):
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(),
    )

    mock_build_env = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=build_venv
    )

    tester.execute("3.7")

    venv_py37 = venv_cache / "{}-py3.7".format(venv_name)
    mock_build_env.assert_called_with(
        venv_py37,
        executable="python3.7",
        flags={"always-copy": False, "system-site-packages": False},
        with_pip=True,
        with_setuptools=True,
        with_wheel=True,
    )

    envs_file = TOMLFile(venv_cache / "envs.toml")
    assert envs_file.exists()
    envs = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

    expected = """\
Creating virtualenv {} in {}
Using virtualenv: {}
""".format(
        venv_py37.name,
        venv_py37.parent,
        venv_py37,
    )

    assert expected == tester.io.fetch_output()


def test_get_prefers_explicitly_activated_virtualenvs_over_env_var(
    tester, current_python, venv_cache, venv_name, venvs_in_cache_config
):
    os.environ["VIRTUAL_ENV"] = "/environment/prefix"

    python_minor = ".".join(str(v) for v in current_python[:2])
    python_patch = ".".join(str(v) for v in current_python[:3])
    venv_dir = venv_cache / "{}-py{}".format(venv_name, python_minor)
    venv_dir.mkdir(parents=True, exist_ok=True)

    envs_file = TOMLFile(venv_cache / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": python_minor, "patch": python_patch}
    envs_file.write(doc)

    tester.execute(python_minor)

    expected = """\
Using virtualenv: {}
""".format(
        venv_dir
    )

    assert expected == tester.io.fetch_output()


def test_get_prefers_explicitly_activated_non_existing_virtualenvs_over_env_var(
    mocker, tester, current_python, venv_cache, venv_name, venvs_in_cache_config
):
    os.environ["VIRTUAL_ENV"] = "/environment/prefix"

    python_minor = ".".join(str(v) for v in current_python[:2])
    venv_dir = venv_cache / "{}-py{}".format(venv_name, python_minor)

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
    mocker.patch("poetry.utils.env.EnvManager.build_venv", side_effect=build_venv)

    tester.execute(python_minor)

    expected = """\
Creating virtualenv {} in {}
Using virtualenv: {}
""".format(
        venv_dir.name,
        venv_dir.parent,
        venv_dir,
    )

    assert expected == tester.io.fetch_output()
