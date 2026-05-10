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
    ("constraint", "implementation", "free_threaded", "expected"),
    [
        (None, None, None, 5),
        (None, "CPython", None, 4),
        (None, "cpython", None, 4),
        (None, "pypy", None, 1),
        ("~3.9", None, None, 2),
        ("~3.9", "cpython", None, 2),
        ("~3.9", "pypy", None, 0),
        (">=3.9.2", None, None, 4),
        (">=3.9.2", "cpython", None, 3),
        (">=3.9.2", "pypy", None, 1),
        (">=3.10", None, None, 3),
        (">=3.10", None, False, 2),
        (">=3.10", None, True, 1),
        ("~3.11", None, None, 0),
    ],
)
def test_find_all_versions(
    mocked_python_register: MockedPythonRegister,
    constraint: str | None,
    implementation: str | None,
    free_threaded: bool | None,
    expected: int,
) -> None:
    mocked_python_register("3.9.1", implementation="CPython", parent="a")
    mocked_python_register("3.9.3", implementation="CPython", parent="b")
    mocked_python_register("3.10.4", implementation="PyPy", parent="c")
    mocked_python_register("3.14.0", implementation="CPython", parent="d")
    mocked_python_register(
        "3.14.0", implementation="CPython", free_threaded=True, parent="e"
    )

    versions = list(Python.find_all_versions(constraint, implementation, free_threaded))
    assert len(versions) == expected


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
                parsed_constraint.allows(
                    Version.parse(f"{v.major}.{v.minor}.{v.patch}")
                )
                for v in versions
            )
        else:
            assert len({v.free_threaded for v in versions}) == 2
            assert len({v.implementation for v in versions}) >= 2


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
