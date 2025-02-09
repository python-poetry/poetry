from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.console.exceptions import PoetryRuntimeError
from poetry.utils.env.python.installer import PythonDownloadNotFoundError
from poetry.utils.env.python.installer import PythonInstallationError


if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from tests.types import CommandTesterFactory


@pytest.fixture(autouse=True)
def mock_installer(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("poetry.console.commands.python.install.PythonInstaller")


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("python install")


def test_install_invalid_version(tester: CommandTester) -> None:
    tester.execute("foo")

    assert tester.status_code == 1
    assert tester.io.fetch_error() == "Invalid Python version requested foo\n"


def test_install_free_threaded_not_supported(tester: CommandTester) -> None:
    tester.execute("-t 3.12")

    assert tester.status_code == 1
    assert (
        "Free threading is not supported for Python versions prior to 3.13.0.\n"
        in tester.io.fetch_error()
    )


def test_install_exists(tester: CommandTester, mock_installer: MagicMock) -> None:
    mock_installer.return_value.exists.return_value = True

    tester.execute("3.11")

    mock_installer.assert_called_once_with("3.11", "cpython", False)
    mock_installer.return_value.install.assert_not_called()

    assert tester.status_code == 1
    assert "Python version already installed at" in tester.io.fetch_error()


def test_install_no_download(tester: CommandTester, mock_installer: MagicMock) -> None:
    mock_installer.return_value.exists.side_effect = PythonDownloadNotFoundError

    tester.execute("3.11")

    mock_installer.assert_called_once_with("3.11", "cpython", False)
    mock_installer.return_value.install.assert_not_called()

    assert tester.status_code == 1
    assert (
        "No suitable standalone build found for the requested Python version.\n"
        in tester.io.fetch_error()
    )


def test_install_failure(tester: CommandTester, mock_installer: MagicMock) -> None:
    mock_installer.return_value.exists.return_value = False
    mock_installer.return_value.install.side_effect = PythonInstallationError("foo")

    tester.execute("3.11")

    mock_installer.assert_called_once_with("3.11", "cpython", False)
    mock_installer.return_value.install.assert_called_once()

    assert tester.status_code == 1
    assert (
        tester.io.fetch_output()
        == "Downloading and installing 3.11 (cpython) ... Failed\n"
    )
    assert "foo\n" in tester.io.fetch_error()


def test_install_corrupt(tester: CommandTester, mock_installer: MagicMock) -> None:
    mock_installer.return_value.exists.side_effect = [False, PoetryRuntimeError("foo")]

    with pytest.raises(PoetryRuntimeError):
        tester.execute("3.11")

    mock_installer.assert_called_once_with("3.11", "cpython", False)
    mock_installer.return_value.install.assert_called_once()

    assert tester.io.fetch_output() == (
        "Downloading and installing 3.11 (cpython) ... Done\n"
        "Testing 3.11 (cpython) ... Failed\n"
    )


def test_install_success(tester: CommandTester, mock_installer: MagicMock) -> None:
    mock_installer.return_value.exists.return_value = False

    tester.execute("3.11")

    mock_installer.assert_called_once_with("3.11", "cpython", False)
    mock_installer.return_value.install.assert_called_once()

    assert tester.status_code == 0
    assert tester.io.fetch_output() == (
        "Downloading and installing 3.11 (cpython) ... Done\n"
        "Testing 3.11 (cpython) ... Done\n"
    )


def test_install_reinstall(tester: CommandTester, mock_installer: MagicMock) -> None:
    mock_installer.return_value.exists.return_value = True

    tester.execute("-r 3.11")

    mock_installer.assert_called_once_with("3.11", "cpython", False)
    mock_installer.return_value.install.assert_called_once()

    assert tester.status_code == 0
    assert tester.io.fetch_output() == (
        "Downloading and installing 3.11 (cpython) ... Done\n"
        "Testing 3.11 (cpython) ... Done\n"
    )


@pytest.mark.parametrize("free_threaded", [False, True])
@pytest.mark.parametrize("implementation", ["cpython", "pypy"])
def test_install_passes_options_to_installer(
    tester: CommandTester,
    mock_installer: MagicMock,
    free_threaded: bool,
    implementation: str,
) -> None:
    mock_installer.return_value.exists.return_value = False

    free_threaded_opt = "-t " if free_threaded else ""
    impl_opt = f"-i {implementation} "
    tester.execute(f"{free_threaded_opt}{impl_opt}3.13")

    mock_installer.assert_called_once_with("3.13", implementation, free_threaded)
    mock_installer.return_value.install.assert_called_once()

    assert tester.status_code == 0
    details = f"{implementation}, free-threaded" if free_threaded else implementation
    assert tester.io.fetch_output() == (
        f"Downloading and installing 3.13 ({details}) ... Done\n"
        f"Testing 3.13 ({details}) ... Done\n"
    )
