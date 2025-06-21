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

    tester.execute("3.9.1")

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

    tester.execute(f"3.9.1 -i {implementation}")

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
