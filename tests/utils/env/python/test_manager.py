from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.core.constraints.version import Version
from poetry.core.constraints.version import parse_constraint

from poetry.utils.env.python import Python


if TYPE_CHECKING:
    from pathlib import Path

    from tests.types import MockedPythonRegister


def test_find_all(without_mocked_findpython: None) -> None:
    assert len(list(Python.find_all())) > 1


def test_find_all_with_poetry_managed(
    without_mocked_findpython: None,
    poetry_managed_pythons: list[Path],
) -> None:
    found_pythons = list(Python.find_all())
    assert len(found_pythons) > len(poetry_managed_pythons)
    for poetry_python in poetry_managed_pythons:
        assert any(p.executable.parent == poetry_python for p in found_pythons)


def test_find_poetry_managed_pythons_none() -> None:
    assert list(Python.find_poetry_managed_pythons()) == []


def test_find_poetry_managed_pythons(poetry_managed_pythons: list[Path]) -> None:
    assert len(list(Python.find_poetry_managed_pythons())) == 2


@pytest.mark.parametrize(
    ("constraint", "expected"),
    [
        (None, 3),
        ("~3.9", 2),
        (">=3.9.2", 2),
        (">=3.10", 1),
        ("~3.11", 0),
    ],
)
def test_find_all_versions(
    mocked_python_register: MockedPythonRegister, constraint: str | None, expected: int
) -> None:
    mocked_python_register("3.9.1", parent="a")
    mocked_python_register("3.9.3", parent="b")
    mocked_python_register("3.10.4", parent="c")

    assert len(list(Python.find_all_versions(constraint))) == expected


@pytest.mark.parametrize("constraint", [None, "~3.9", ">=3.10"])
def test_find_downloadable_versions(constraint: str | None) -> None:
    versions = Python.find_downloadable_versions(constraint)
    if constraint:
        parsed_constraint = parse_constraint(constraint)
        assert all(
            parsed_constraint.allows(Version.parse(f"{v.major}.{v.minor}.{v.patch}"))
            for v in versions
        )
    else:
        assert len(list(versions)) > 0


def find_downloadable_versions_include_incompatible() -> None:
    assert len(
        list(Python.find_downloadable_versions(include_incompatible=True))
    ) > len(list(Python.find_downloadable_versions()))
