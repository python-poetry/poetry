from __future__ import annotations

from typing import TYPE_CHECKING

import packaging.version
import pytest

from findpython import PythonVersion

from poetry.utils._compat import WINDOWS


if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from poetry.config.config import Config


class MockPythonVersion(PythonVersion):  # type: ignore[misc]
    def _get_version(self) -> packaging.version.Version:
        return packaging.version.Version(self.executable.parent.name.split("@")[1])

    def _get_interpreter(self) -> str:
        return str(self.executable)


@pytest.fixture
def mock_python_version(mocker: MockerFixture) -> None:
    mocker.patch(
        "poetry.utils.env.python.providers.PoetryPythonPathProvider.version_maker",
        MockPythonVersion,
    )


@pytest.fixture
def poetry_managed_pythons(config: Config, mock_python_version: None) -> list[Path]:
    config.python_installation_dir.mkdir()

    # CPython
    cpython_dir = config.python_installation_dir / "cpython@3.9.1"
    if not WINDOWS:
        cpython_dir /= "bin"
    cpython_dir.mkdir(parents=True)
    (cpython_dir / "python").touch()

    # PyPy
    pypy_dir = config.python_installation_dir / "pypy@3.10.8"
    if not WINDOWS:
        pypy_dir /= "bin"
    pypy_dir.mkdir(parents=True)
    (pypy_dir / "pypy").touch()

    return [cpython_dir, pypy_dir]
