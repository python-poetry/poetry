<<<<<<< HEAD
from typing import TYPE_CHECKING
from typing import List

=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
import pytest
import tomlkit

from poetry.core.toml.file import TOMLFile


<<<<<<< HEAD
if TYPE_CHECKING:
    from pathlib import Path

    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.utils.env import MockEnv
    from tests.types import CommandTesterFactory


@pytest.fixture
def venv_activate_37(venv_cache: "Path", venv_name: str) -> None:
=======
@pytest.fixture
def venv_activate_37(venv_cache, venv_name):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    envs_file = TOMLFile(venv_cache / "envs.toml")
    doc = tomlkit.document()
    doc[venv_name] = {"minor": "3.7", "patch": "3.7.0"}
    envs_file.write(doc)


@pytest.fixture
<<<<<<< HEAD
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
    return command_tester_factory("env list")


def test_none_activated(
    tester: "CommandTester",
    venvs_in_cache_dirs: List[str],
    mocker: "MockerFixture",
    env: "MockEnv",
):
=======
def tester(command_tester_factory):
    return command_tester_factory("env list")


def test_none_activated(tester, venvs_in_cache_dirs, mocker, env):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=env)
    tester.execute()
    expected = "\n".join(venvs_in_cache_dirs).strip()
    assert expected == tester.io.fetch_output().strip()


<<<<<<< HEAD
def test_activated(
    tester: "CommandTester",
    venvs_in_cache_dirs: List[str],
    venv_cache: "Path",
    venv_activate_37: None,
):
=======
def test_activated(tester, venvs_in_cache_dirs, venv_cache, venv_activate_37):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute()
    expected = (
        "\n".join(venvs_in_cache_dirs).strip().replace("py3.7", "py3.7 (Activated)")
    )
    assert expected == tester.io.fetch_output().strip()


<<<<<<< HEAD
def test_in_project_venv(tester: "CommandTester", venvs_in_project_dir: List[str]):
=======
def test_in_project_venv(tester, venvs_in_project_dir):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute()
    expected = ".venv (Activated)\n"
    assert expected == tester.io.fetch_output()
