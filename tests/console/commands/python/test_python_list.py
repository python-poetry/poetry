from __future__ import annotations

import platform

from typing import TYPE_CHECKING

import pytest

from poetry.utils._compat import WINDOWS
from tests.helpers import pbs_installer_supported_arch


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.config.config import Config
    from tests.types import CommandTesterFactory
    from tests.types import MockedPythonRegister


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("python list")


def test_list_no_versions(tester: CommandTester) -> None:
    tester.execute()

    assert tester.io.fetch_output() == "No Python installations found.\n"


def test_list_all(tester: CommandTester) -> None:
    tester.execute("--all")

    if platform.system() == "FreeBSD" or not pbs_installer_supported_arch(
        platform.machine()
    ):
        assert tester.io.fetch_output() == "No Python installations found.\n"
    else:
        assert "Available for download" in tester.io.fetch_output()


def test_list_invalid_version(tester: CommandTester) -> None:
    tester.execute("foo")

    assert tester.status_code == 1
    assert tester.io.fetch_error() == "Invalid Python version requested foo\n"


def test_list(
    tester: CommandTester, mocked_python_register: MockedPythonRegister
) -> None:
    mocked_python_register("3.9.1", parent="a")
    mocked_python_register("3.9.3", parent="b")
    mocked_python_register("3.10.4", parent="c")

    tester.execute()

    expected = """\
 Version Implementation Manager Path         \

 3.10.4  CPython        System  c/python3.10 \

 3.9.3   CPython        System  b/python3.9  \

 3.9.1   CPython        System  a/python3.9  \

"""

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize("only_poetry_managed", [False, True])
def test_list_poetry_managed(
    tester: CommandTester,
    config: Config,
    mocked_python_register: MockedPythonRegister,
    only_poetry_managed: bool,
) -> None:
    # Register mocked system Pythons
    mocked_python_register("3.11.5", parent="s")
    mocked_python_register("3.12.3", parent="t")

    # Register mocked poetry-managed Pythons via their installation paths
    install_dir = config.python_installation_dir
    install_dir.mkdir(exist_ok=True)

    # We cannot use mocked_poetry_managed_python_register here because it deactivates mocking of system Pythons
    for implementation, version in [
        ("CPython", "3.9.1"),
        ("PyPy", "3.10.8"),
        ("CPython", "3.14.0t"),
    ]:
        bin_path = (
            install_dir
            / f"{implementation.lower()}@{version}"
            / ("" if WINDOWS else "bin")
        )
        bin_path.mkdir(parents=True)
        executables = ["python"]
        if implementation == "PyPy":
            executables.append("pypy")
        for executable in executables:
            mocked_python_register(
                version.removesuffix("t"),
                executable_name=executable,
                implementation=implementation,
                parent=bin_path,
                free_threaded=version.endswith("t"),
            )

    tester.execute("-m" if only_poetry_managed else "")

    lines = tester.io.fetch_output().splitlines()
    system_lines = [line.strip() for line in lines if "System" in line]
    poetry_lines = [line.strip() for line in lines if "Poetry" in line]

    expected_system = {
        "3.11.5  CPython        System  s/python3.11",
        "3.12.3  CPython        System  t/python3.12",
    }

    bin_dir = "" if WINDOWS else "bin/"
    expected_poetry = {
        f"3.10.8  PyPy           Poetry  {install_dir.as_posix()}/pypy@3.10.8/{bin_dir}pypy",
        f"3.10.8  PyPy           Poetry  {install_dir.as_posix()}/pypy@3.10.8/{bin_dir}python",
        f"3.9.1   CPython        Poetry  {install_dir.as_posix()}/cpython@3.9.1/{bin_dir}python",
        f"3.14.0t CPython        Poetry  {install_dir.as_posix()}/cpython@3.14.0t/{bin_dir}python",
    }

    assert set(poetry_lines) == expected_poetry
    if only_poetry_managed:
        assert not system_lines
    else:
        assert set(system_lines) == expected_system


@pytest.mark.parametrize(
    ("version", "expected"),
    [("3", 3), ("3.9", 2), ("3.9.2", 0), ("3.9.3", 1)],
)
def test_list_version(
    tester: CommandTester,
    mocked_python_register: MockedPythonRegister,
    version: str,
    expected: int,
) -> None:
    mocked_python_register("2.7.13", parent="_")
    mocked_python_register("3.9.1", parent="a")
    mocked_python_register("3.9.3", parent="b")
    mocked_python_register("3.10.4", parent="c")

    tester.execute(version)

    assert len(tester.io.fetch_output().splitlines()) - 1 == expected


@pytest.mark.parametrize(
    ("implementation", "expected"), [("PyPy", 1), ("pypy", 1), ("CPython", 2)]
)
def test_list_implementation(
    tester: CommandTester,
    mocked_python_register: MockedPythonRegister,
    implementation: str,
    expected: int,
) -> None:
    mocked_python_register("3.9.1", implementation="PyPy", parent="a")
    mocked_python_register("3.9.3", implementation="CPython", parent="b")
    mocked_python_register("3.10.4", implementation="CPython", parent="c")

    tester.execute(f"-i {implementation}")

    assert len(tester.io.fetch_output().splitlines()) - 1 == expected


@pytest.mark.parametrize(("free_threaded", "expected"), [("-t", 1), ("", 3)])
def test_list_free_threaded(
    tester: CommandTester,
    mocked_python_register: MockedPythonRegister,
    free_threaded: str,
    expected: int,
) -> None:
    mocked_python_register("3.13.0", free_threaded=False, parent="a")
    mocked_python_register("3.14.0", free_threaded=False, parent="b")
    mocked_python_register("3.14.0", free_threaded=True, parent="c")

    tester.execute(free_threaded)

    assert len(tester.io.fetch_output().splitlines()) - 1 == expected
