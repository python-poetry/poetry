from __future__ import annotations

import os

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest
import tomlkit

from poetry.core.constraints.version import Version

from poetry.console.commands.env.use import EnvUseCommand
from poetry.toml.file import TOMLFile
from poetry.utils.env import MockEnv
from poetry.utils.env.python.exceptions import NoCompatiblePythonVersionFoundError
from tests.console.commands.env.helpers import build_venv
from tests.console.commands.env.helpers import check_output_wrapper


if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.utils.env.base_env import PythonVersion
    from tests.types import CommandTesterFactory
    from tests.types import MockedPythonRegister


@pytest.fixture(autouse=True)
def setup(mocker: MockerFixture) -> None:
    if "VIRTUAL_ENV" in os.environ:
        del os.environ["VIRTUAL_ENV"]


@pytest.fixture(autouse=True)
def mock_subprocess_calls(
    setup: None, current_python: PythonVersion, mocker: MockerFixture
) -> None:
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.from_parts(*current_python[:3])),
    )
    mocker.patch(
        "subprocess.Popen.communicate",
        side_effect=[("/prefix", None), ("/prefix", None), ("/prefix", None)],
    )


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("env use")


def test_activate_activates_non_existing_virtualenv_no_envs_file(
    mocker: MockerFixture,
    tester: CommandTester,
    venv_cache: Path,
    venv_name: str,
    venvs_in_cache_config: None,
    mocked_python_register: MockedPythonRegister,
    with_no_active_python: MagicMock,
) -> None:
    mocked_python_register("3.7.1")
    mock_build_env = mocker.patch(
        "poetry.utils.env.EnvManager.build_venv", side_effect=build_venv
    )
    envs_file = TOMLFile(venv_cache / "envs.toml")

    assert not envs_file.exists()
    assert not list(venv_cache.iterdir())

    tester.execute("3.7")

    venv_py37 = venv_cache / f"{venv_name}-py3.7"
    mock_build_env.assert_called_with(
        venv_py37,
        executable=Path("/usr/bin/python3.7"),
        flags={
            "always-copy": False,
            "system-site-packages": False,
            "no-pip": False,
        },
        prompt="simple-project-py3.7",
    )

    assert envs_file.exists()
    envs: dict[str, Any] = envs_file.read()
    assert envs[venv_name]["minor"] == "3.7"
    assert envs[venv_name]["patch"] == "3.7.1"

    assert (
        tester.io.fetch_error()
        == f"Creating virtualenv {venv_py37.name} in {venv_py37.parent}\n"
    )
    assert tester.io.fetch_output() == f"Using virtualenv: {venv_py37}\n"


@pytest.mark.parametrize("use_poetry_python", [True, False])
def test_activate_does_not_activate_non_existing_virtualenv_with_unsupported_version(
    tester: CommandTester,
    venv_cache: Path,
    venv_name: str,
    venvs_in_cache_config: None,
    mocked_python_register: MockedPythonRegister,
    with_no_active_python: MagicMock,
    use_poetry_python: bool,
) -> None:
    mocked_python_register("3.7.1")
    mocked_python_register("3.8.2")
    command = tester.command
    assert isinstance(command, EnvUseCommand)
    command.poetry.package.python_versions = "~3.8"
    command.poetry.config.merge(
        {"virtualenvs": {"use-poetry-python": use_poetry_python}}
    )

    assert not list(venv_cache.iterdir())

    with pytest.raises(NoCompatiblePythonVersionFoundError):
        tester.execute("3.7")

    assert not list(venv_cache.iterdir())


def test_get_prefers_explicitly_activated_virtualenvs_over_env_var(
    tester: CommandTester,
    current_python: PythonVersion,
    venv_cache: Path,
    venv_name: str,
    venvs_in_cache_config: None,
    mocked_python_register: MockedPythonRegister,
) -> None:
    os.environ["VIRTUAL_ENV"] = "/environment/prefix"

    python_minor = ".".join(str(v) for v in current_python[:2])
    python_patch = ".".join(str(v) for v in current_python[:3])
    venv_dir = venv_cache / f"{venv_name}-py{python_minor}"
    venv_dir.mkdir(parents=True, exist_ok=True)

    envs_file = TOMLFile(venv_cache / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": python_minor, "patch": python_patch}
    envs_file.write(doc)

    mocked_python_register(python_patch)

    tester.execute(python_minor)

    expected = f"""\
Using virtualenv: {venv_dir}
"""

    assert tester.io.fetch_output() == expected


def test_get_prefers_explicitly_activated_non_existing_virtualenvs_over_env_var(
    mocker: MockerFixture,
    tester: CommandTester,
    current_python: PythonVersion,
    venv_cache: Path,
    venv_name: str,
    venvs_in_cache_config: None,
    mocked_python_register: MockedPythonRegister,
) -> None:
    os.environ["VIRTUAL_ENV"] = "/environment/prefix"

    python_minor = ".".join(str(v) for v in current_python[:2])
    venv_dir = venv_cache / f"{venv_name}-py{python_minor}"

    mocked_python_register(python_minor)

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

    assert (
        tester.io.fetch_error()
        == f"Creating virtualenv {venv_dir.name} in {venv_dir.parent}\n"
    )
    assert tester.io.fetch_output() == f"Using virtualenv: {venv_dir}\n"
