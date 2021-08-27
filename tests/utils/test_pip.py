import subprocess

<<<<<<< HEAD
from typing import TYPE_CHECKING

import pytest

from poetry.core.packages.utils.link import Link
from poetry.core.packages.utils.utils import path_to_url

from poetry.utils.pip import pip_install


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from poetry.utils.env import VirtualEnv
    from tests.types import FixtureDirGetter


def test_pip_install_successful(
    tmp_dir: str, tmp_venv: "VirtualEnv", fixture_dir: "FixtureDirGetter"
):
=======
import pytest

from poetry.utils.pip import pip_install


def test_pip_install_successful(tmp_dir, tmp_venv, fixture_dir):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    file_path = fixture_dir("distributions/demo-0.1.0-py2.py3-none-any.whl")
    result = pip_install(file_path, tmp_venv)

    assert "Successfully installed demo-0.1.0" in result


<<<<<<< HEAD
def test_pip_install_link(
    tmp_dir: str, tmp_venv: "VirtualEnv", fixture_dir: "FixtureDirGetter"
):
    file_path = Link(
        path_to_url(fixture_dir("distributions/demo-0.1.0-py2.py3-none-any.whl"))
    )
    result = pip_install(file_path, tmp_venv)

    assert "Successfully installed demo-0.1.0" in result


def test_pip_install_with_keyboard_interrupt(
    tmp_dir: str,
    tmp_venv: "VirtualEnv",
    fixture_dir: "FixtureDirGetter",
    mocker: "MockerFixture",
):
=======
def test_pip_install_with_keyboard_interrupt(tmp_dir, tmp_venv, fixture_dir, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    file_path = fixture_dir("distributions/demo-0.1.0-py2.py3-none-any.whl")
    mocker.patch("subprocess.run", side_effect=KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        pip_install(file_path, tmp_venv)
    subprocess.run.assert_called_once()
