from __future__ import annotations

import platform
import sys

from typing import TYPE_CHECKING

import pytest

from poetry.core.constraints.version import Version
from poetry.core.constraints.version import parse_constraint

from poetry.utils.env.python import Python
from tests.helpers import pbs_installer_supported_arch


if TYPE_CHECKING:
    from tests.types import MockedPoetryPythonRegister
    from tests.types import MockedPythonRegister


def test_find_all(without_mocked_findpython: None) -> None:
    assert len(list(Python.find_all())) > 1


def test_find_all_with_poetry_managed(
    without_mocked_findpython: None,
    mocked_poetry_managed_python_register: MockedPoetryPythonRegister,
) -> None:
    cpython_path = mocked_poetry_managed_python_register("3.9.1", "cpython")
    pypy_path = mocked_poetry_managed_python_register("3.10.8", "pypy")
    found_pythons = list(Python.find_all())
    assert len(found_pythons) > 3
    for poetry_python in (cpython_path, pypy_path):
        assert any(p.executable.parent == poetry_python for p in found_pythons)


def test_find_poetry_managed_pythons_none() -> None:
    assert list(Python.find_poetry_managed_pythons()) == []


def test_find_poetry_managed_pythons(
    mocked_poetry_managed_python_register: MockedPoetryPythonRegister,
) -> None:
    mocked_poetry_managed_python_register("3.9.1", "cpython")
    mocked_poetry_managed_python_register("3.10.8", "pypy")

    assert len(list(Python.find_poetry_managed_pythons())) == 3


@pytest.mark.parametrize(
    ("constraint", "implementation", "expected"),
    [
        (None, None, 3),
        (None, "CPython", 2),
        (None, "cpython", 2),
        (None, "pypy", 1),
        ("~3.9", None, 2),
        ("~3.9", "cpython", 2),
        ("~3.9", "pypy", 0),
        (">=3.9.2", None, 2),
        (">=3.9.2", "cpython", 1),
        (">=3.9.2", "pypy", 1),
        (">=3.10", None, 1),
        ("~3.11", None, 0),
    ],
)
def test_find_all_versions(
    mocked_python_register: MockedPythonRegister,
    constraint: str | None,
    implementation: str | None,
    expected: int,
) -> None:
    mocked_python_register("3.9.1", implementation="CPython", parent="a")
    mocked_python_register("3.9.3", implementation="CPython", parent="b")
    mocked_python_register("3.10.4", implementation="PyPy", parent="c")

    assert len(list(Python.find_all_versions(constraint, implementation))) == expected


@pytest.mark.parametrize("constraint", [None, "~3.9", ">=3.10"])
def test_find_downloadable_versions(constraint: str | None) -> None:
    versions = list(Python.find_downloadable_versions(constraint))
    if platform.system() == "FreeBSD" or not pbs_installer_supported_arch(
        platform.machine()
    ):
        assert len(versions) == 0
    else:
        assert len(versions) > 0
    if constraint:
        parsed_constraint = parse_constraint(constraint)
        assert all(
            parsed_constraint.allows(Version.parse(f"{v.major}.{v.minor}.{v.patch}"))
            for v in versions
        )


def find_downloadable_versions_include_incompatible() -> None:
    assert len(
        list(Python.find_downloadable_versions(include_incompatible=True))
    ) > len(list(Python.find_downloadable_versions()))


@pytest.mark.parametrize(
    ("name", "expected_minor"),
    [
        ("3.9", 9),
        ("3.10", 10),
        ("3.11", None),
    ],
)
def test_get_by_name_version(
    mocked_python_register: MockedPythonRegister, name: str, expected_minor: int | None
) -> None:
    mocked_python_register("3.9.1", implementation="CPython", parent="a")
    mocked_python_register("3.10.3", implementation="CPython", parent="b")

    python = Python.get_by_name(name)
    if expected_minor is None:
        assert python is None
    else:
        assert python is not None
        assert python.minor == expected_minor


def test_get_by_name_python(without_mocked_findpython: None) -> None:
    python = Python.get_by_name("python")
    assert python is not None
    assert python.version.major == 3
    assert python.version.minor == sys.version_info.minor


def test_get_by_name_path(without_mocked_findpython: None) -> None:
    python = Python.get_by_name(sys.executable)
    assert python is not None
    assert python.version.major == 3
    assert python.version.minor == sys.version_info.minor
