from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.config.config import Config
    from tests.types import CommandTesterFactory
    from tests.types import MockedPoetryPythonRegister


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("python remove")


def test_remove_invalid_version(tester: CommandTester) -> None:
    tester.execute("foo")

    assert tester.status_code == 1
    assert tester.io.fetch_error() == "Invalid Python version requested foo\n"


def test_remove_version_not_precise_enough(tester: CommandTester) -> None:
    tester.execute("3.9")

    assert tester.status_code == 1
    assert (
        tester.io.fetch_error()
        == """\
Invalid Python version requested 3.9

You need to provide an exact Python version in the format X.Y.Z to be removed.

You can use poetry python list -m to list installed Poetry managed Python versions.
"""
    )


def test_remove_version_no_installation(tester: CommandTester, config: Config) -> None:
    tester.execute("3.9.1")

    location = config.python_installation_dir / "cpython@3.9.1"
    assert tester.io.fetch_output() == f"No installation was found at {location}.\n"


def test_remove_version(
    tester: CommandTester,
    config: Config,
    mocked_poetry_managed_python_register: MockedPoetryPythonRegister,
) -> None:
    cpython_path = mocked_poetry_managed_python_register("3.9.1", "cpython")
    other_cpython_path = mocked_poetry_managed_python_register("3.9.2", "cpython")
    pypy_path = mocked_poetry_managed_python_register("3.9.1", "pypy")

    assert tester.execute("3.9.1") == 0, tester.io.fetch_error()

    assert (
        tester.io.fetch_output() == "Removing installation 3.9.1 (cpython) ... Done\n"
    )
    assert not cpython_path.exists()
    assert pypy_path.exists()
    assert other_cpython_path.exists()


@pytest.mark.parametrize("implementation", ["cpython", "pypy"])
def test_remove_version_implementation(
    tester: CommandTester,
    config: Config,
    mocked_poetry_managed_python_register: MockedPoetryPythonRegister,
    implementation: str,
) -> None:
    cpython_path = mocked_poetry_managed_python_register("3.9.1", "cpython")
    pypy_path = mocked_poetry_managed_python_register("3.9.1", "pypy")

    assert tester.execute(f"3.9.1 -i {implementation}") == 0, tester.io.fetch_error()

    assert (
        tester.io.fetch_output()
        == f"Removing installation 3.9.1 ({implementation}) ... Done\n"
    )
    if implementation == "cpython":
        assert not cpython_path.exists()
        assert pypy_path.exists()
    else:
        assert cpython_path.exists()
        assert not pypy_path.exists()


@pytest.mark.parametrize("free_threaded", [True, False])
@pytest.mark.parametrize("option", [True, False])
def test_remove_version_free_threaded(
    tester: CommandTester,
    config: Config,
    mocked_poetry_managed_python_register: MockedPoetryPythonRegister,
    free_threaded: bool,
    option: bool,
) -> None:
    standard_path = mocked_poetry_managed_python_register("3.14.0", "cpython")
    free_threaded_path = mocked_poetry_managed_python_register(
        "3.14.0", "cpython", free_threaded=True
    )

    args = "3.14.0"
    if free_threaded:
        args += " --free-threaded" if option else "t"

    assert tester.execute(args) == 0, tester.io.fetch_error()

    details = "cpython"
    if free_threaded:
        details += ", free-threaded"
    assert (
        tester.io.fetch_output()
        == f"Removing installation 3.14.0 ({details}) ... Done\n"
    )
    if free_threaded:
        assert not free_threaded_path.exists()
        assert standard_path.exists()
    else:
        assert not standard_path.exists()
        assert free_threaded_path.exists()


def test_remove_multiple_versions(
    tester: CommandTester,
    config: Config,
    mocked_poetry_managed_python_register: MockedPoetryPythonRegister,
) -> None:
    cpython_path_1 = mocked_poetry_managed_python_register("3.9.1", "cpython")
    cpython_path_2 = mocked_poetry_managed_python_register("3.9.2", "cpython")
    cpython_path_3 = mocked_poetry_managed_python_register("3.9.3", "cpython")

    tester.execute("3.9.1 3.9.3")

    assert tester.io.fetch_output() == (
        "Removing installation 3.9.1 (cpython) ... Done\n"
        "Removing installation 3.9.3 (cpython) ... Done\n"
    )
    assert not cpython_path_1.exists()
    assert cpython_path_2.exists()
    assert not cpython_path_3.exists()
