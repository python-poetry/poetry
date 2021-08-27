<<<<<<< HEAD
from typing import TYPE_CHECKING
from typing import List

import pytest

from poetry.core.semver.version import Version

from tests.console.commands.env.helpers import check_output_wrapper


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
=======
import pytest

from poetry.core.semver.version import Version
from tests.console.commands.env.helpers import check_output_wrapper


@pytest.fixture
def tester(command_tester_factory):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return command_tester_factory("env remove")


def test_remove_by_python_version(
<<<<<<< HEAD
    mocker: "MockerFixture",
    tester: "CommandTester",
    venvs_in_cache_dirs: List[str],
    venv_name: str,
    venv_cache: "Path",
=======
    mocker, tester, venvs_in_cache_dirs, venv_name, venv_cache
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    check_output = mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.6.6")),
    )

    tester.execute("3.6")

    assert check_output.called
<<<<<<< HEAD
    assert not (venv_cache / f"{venv_name}-py3.6").exists()

    expected = f"Deleted virtualenv: {venv_cache / venv_name}-py3.6\n"
    assert expected == tester.io.fetch_output()


def test_remove_by_name(
    tester: "CommandTester",
    venvs_in_cache_dirs: List[str],
    venv_name: str,
    venv_cache: "Path",
):
=======
    assert not (venv_cache / "{}-py3.6".format(venv_name)).exists()

    expected = "Deleted virtualenv: {}\n".format(
        (venv_cache / "{}-py3.6".format(venv_name))
    )
    assert expected == tester.io.fetch_output()


def test_remove_by_name(tester, venvs_in_cache_dirs, venv_name, venv_cache):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    expected = ""

    for name in venvs_in_cache_dirs:
        tester.execute(name)

        assert not (venv_cache / name).exists()

<<<<<<< HEAD
        expected += f"Deleted virtualenv: {venv_cache / name}\n"

    assert expected == tester.io.fetch_output()


def test_remove_all(
    tester: "CommandTester",
    venvs_in_cache_dirs: List[str],
    venv_name: str,
    venv_cache: "Path",
):
    expected = {""}
    tester.execute("--all")
    for name in venvs_in_cache_dirs:
        assert not (venv_cache / name).exists()
        expected.add(f"Deleted virtualenv: {venv_cache / name}")
    assert expected == set(tester.io.fetch_output().split("\n"))


def test_remove_all_and_version(
    tester: "CommandTester",
    venvs_in_cache_dirs: List[str],
    venv_name: str,
    venv_cache: "Path",
):
    expected = {""}
    tester.execute(f"--all {venvs_in_cache_dirs[0]}")
    for name in venvs_in_cache_dirs:
        assert not (venv_cache / name).exists()
        expected.add(f"Deleted virtualenv: {venv_cache / name}")
    assert expected == set(tester.io.fetch_output().split("\n"))


def test_remove_multiple(
    tester: "CommandTester",
    venvs_in_cache_dirs: List[str],
    venv_name: str,
    venv_cache: "Path",
):
    expected = {""}
    removed_envs = venvs_in_cache_dirs[0:2]
    remaining_envs = venvs_in_cache_dirs[2:]
    tester.execute(" ".join(removed_envs))
    for name in removed_envs:
        assert not (venv_cache / name).exists()
        expected.add(f"Deleted virtualenv: {venv_cache / name}")
    for name in remaining_envs:
        assert (venv_cache / name).exists()
    assert expected == set(tester.io.fetch_output().split("\n"))
=======
        expected += "Deleted virtualenv: {}\n".format((venv_cache / name))

    assert expected == tester.io.fetch_output()
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
