import subprocess

from typing import TYPE_CHECKING
from typing import Callable

import pytest

from poetry.core.packages.utils.link import Link
from poetry.core.packages.utils.utils import path_to_url
from poetry.utils.pip import pip_install


if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from poetry.utils.env import VirtualEnv


def test_pip_install_successful(
    tmp_dir: str, tmp_venv: "VirtualEnv", fixture_dir: Callable[[str], "Path"]
):
    file_path = fixture_dir("distributions/demo-0.1.0-py2.py3-none-any.whl")
    result = pip_install(file_path, tmp_venv)

    assert "Successfully installed demo-0.1.0" in result


def test_pip_install_link(
    tmp_dir: str, tmp_venv: "VirtualEnv", fixture_dir: Callable[[str], "Path"]
):
    file_path = Link(
        path_to_url(fixture_dir("distributions/demo-0.1.0-py2.py3-none-any.whl"))
    )
    result = pip_install(file_path, tmp_venv)

    assert "Successfully installed demo-0.1.0" in result


def test_pip_install_with_keyboard_interrupt(
    tmp_dir: str,
    tmp_venv: "VirtualEnv",
    fixture_dir: Callable[[str], "Path"],
    mocker: "MockerFixture",
):
    file_path = fixture_dir("distributions/demo-0.1.0-py2.py3-none-any.whl")
    mocker.patch("subprocess.run", side_effect=KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        pip_install(file_path, tmp_venv)
    subprocess.run.assert_called_once()
