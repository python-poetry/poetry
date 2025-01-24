from __future__ import annotations

from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING
from typing import cast

import pytest

from poetry.core.constraints.version import Version

from poetry.console.exceptions import PoetryRuntimeError
from poetry.utils.env.python.installer import PythonDownloadNotFoundError
from poetry.utils.env.python.installer import PythonInstallationError
from poetry.utils.env.python.installer import PythonInstaller


if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def mock_get_download_link(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "pbs_installer.get_download_link",
        return_value=(mocker.Mock(major=3, minor=9, micro=1), None),
    )


def test_python_installer_version() -> None:
    installer = PythonInstaller(request="3.9.1")
    assert installer.version == Version.from_parts(3, 9, 1)


def test_python_installer_version_not_found(mock_get_download_link: MagicMock) -> None:
    mock_get_download_link.return_value = []
    installer = PythonInstaller(request="3.9.1")
    with pytest.raises(PythonDownloadNotFoundError):
        _ = installer.version


def test_python_installer_exists(mocker: MockerFixture) -> None:
    mocker.patch(
        "poetry.utils.env.python.Python.find_poetry_managed_pythons",
        return_value=[
            mocker.Mock(implementation="cpython", version=Version.from_parts(3, 9, 1))
        ],
    )
    installer = PythonInstaller(request="3.9.1")
    assert installer.exists()


def test_python_installer_does_not_exist(mocker: MockerFixture) -> None:
    mocker.patch(
        "poetry.utils.env.python.Python.find_poetry_managed_pythons", return_value=[]
    )
    installer = PythonInstaller(request="3.9.1")
    assert not installer.exists()


def test_python_installer_exists_with_bad_executables(mocker: MockerFixture) -> None:
    class BadPython:
        @property
        def implementation(self) -> str:
            return "cpython"

        @property
        def executable(self) -> Path:
            return cast(Path, mocker.Mock(as_posix=lambda: "/path/to/bad/python"))

        @property
        def version(self) -> None:
            raise CalledProcessError(1, "cmd")

    mocker.patch(
        "poetry.utils.env.python.Python.find_poetry_managed_pythons",
        return_value=[BadPython()],
    )

    installer = PythonInstaller(request="3.9.1")
    with pytest.raises(PoetryRuntimeError):
        assert not installer.exists()


def test_python_installer_install(mocker: MockerFixture) -> None:
    mocker.patch(
        "pbs_installer.get_download_link",
        return_value=(mocker.Mock(major=3, minor=9, micro=1), None),
    )
    install = mocker.patch("pbs_installer.install")
    installer = PythonInstaller(request="3.9.1")
    installer.install()
    install.assert_called_once_with(
        "3.9.1",
        installer.installation_directory,
        True,
        implementation="cpython",
        free_threaded=False,
    )


def test_python_installer_install_error(mocker: MockerFixture) -> None:
    mocker.patch("pbs_installer.install", side_effect=ValueError)
    installer = PythonInstaller(request="3.9.1")
    with pytest.raises(PythonInstallationError):
        installer.install()
