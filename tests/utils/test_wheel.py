from __future__ import annotations

import pytest

from poetry.core.constraints.version import Version
from poetry.core.constraints.version import VersionConstraint
from poetry.core.constraints.version import VersionRange

from poetry.utils.wheel import Wheel


@pytest.mark.parametrize(
    "pyversion, min_version, max_version",
    [
        ("cp39", "3.9.0", "3.10.0"),
        ("cp310", "3.10.0", "3.11.0"),
        ("py2", "2.0.0", "3.0.0"),
        ("py3", "3.0.0", "4.0.0"),
        ("py30", "3.0.0", "3.1.0"),
    ],
)
def test_pyversion_to_constraint(
    pyversion: str, min_version: str, max_version: str
) -> None:
    assert Wheel._pyversion_to_constraint(pyversion) == VersionRange(
        min=Version.parse(min_version),
        max=Version.parse(max_version),
        include_min=True,
        include_max=False,
    )


@pytest.mark.parametrize(
    "wheel_name, python_constraint, expected",
    [
        (
            "foo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            VersionRange(min=Version.parse("3.8.0"), max=Version.parse("3.9.0")),
            True,
        ),
        (
            "foo-0.1.0-cp38-none-macosx_10_15_x86_64.whl",
            VersionRange(min=Version.parse("3.8.0"), max=Version.parse("3.9.0")),
            True,
        ),
        (
            "foo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            VersionRange(min=Version.parse("3.8.0"), max=Version.parse("4.0.0")),
            True,
        ),
        (
            "foo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            VersionRange(min=Version.parse("3.8.2"), max=Version.parse("3.8.5")),
            True,
        ),
        (
            "foo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            Version.parse("3.8.0"),
            True,
        ),
        (
            "foo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            Version.parse("3.8.15"),
            True,
        ),
        (
            "foo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            VersionRange(min=Version.parse("3.8.0"), max=None),
            True,
        ),
        (
            "foo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            VersionRange(min=Version.parse("3.7.0"), max=Version.parse("3.9.0")),
            True,
        ),
        (
            "foo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            VersionRange(min=Version.parse("3.9.0"), max=Version.parse("3.10.0")),
            False,
        ),
        (
            "foo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            Version.parse("3.9.15"),
            False,
        ),
        (
            "foo-0.1.0-py3-none-macosx_10_15_x86_64.whl",
            VersionRange(min=Version.parse("3.9.0"), max=Version.parse("3.10.0")),
            True,
        ),
        (
            "foo-0.1.0-py2-none-macosx_10_15_x86_64.whl",
            VersionRange(min=Version.parse("3.0.0"), max=None),
            False,
        ),
        (
            "foo-0.1.0-py3-none-macosx_10_15_x86_64.whl",
            VersionRange(min=Version.parse("3.0.0"), max=None),
            True,
        ),
        (
            "foo-0.1.0-py2.py3-none-macosx_10_15_x86_64.whl",
            VersionRange(min=Version.parse("2.0.0"), max=Version.parse("2.7.0")),
            True,
        ),
    ],
)
def test_is_compatible_with_python(
    wheel_name: str, python_constraint: VersionConstraint, expected: bool
) -> None:
    wheel = Wheel(wheel_name)
    assert wheel.is_compatible_with_python(python_constraint) is expected
