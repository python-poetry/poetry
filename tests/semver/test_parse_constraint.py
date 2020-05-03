import pytest

from poetry.semver import Version
from poetry.semver import VersionRange
from poetry.semver import VersionUnion
from poetry.semver import parse_constraint


@pytest.mark.parametrize(
    "constraint,version",
    [
        ("~=3.8", VersionRange(min=Version(3, 8), max=Version(4, 0), include_min=True)),
        (
            "~= 3.8",
            VersionRange(min=Version(3, 8), max=Version(4, 0), include_min=True),
        ),
        ("~3.8", VersionRange(min=Version(3, 8), max=Version(3, 9), include_min=True)),
        ("~ 3.8", VersionRange(min=Version(3, 8), max=Version(3, 9), include_min=True)),
        (">3.8", VersionRange(min=Version(3, 8))),
        (">=3.8", VersionRange(min=Version(3, 8), include_min=True)),
        (">= 3.8", VersionRange(min=Version(3, 8), include_min=True)),
        (
            ">3.8,<=6.5",
            VersionRange(min=Version(3, 8), max=Version(6, 5), include_max=True),
        ),
        (
            ">3.8,<= 6.5",
            VersionRange(min=Version(3, 8), max=Version(6, 5), include_max=True),
        ),
        (
            "> 3.8,<= 6.5",
            VersionRange(min=Version(3, 8), max=Version(6, 5), include_max=True),
        ),
        (
            "> 3.8,<=6.5",
            VersionRange(min=Version(3, 8), max=Version(6, 5), include_max=True),
        ),
        (
            ">3.8 ,<=6.5",
            VersionRange(min=Version(3, 8), max=Version(6, 5), include_max=True),
        ),
        (
            ">3.8, <=6.5",
            VersionRange(min=Version(3, 8), max=Version(6, 5), include_max=True),
        ),
        (
            ">3.8 , <=6.5",
            VersionRange(min=Version(3, 8), max=Version(6, 5), include_max=True),
        ),
        (
            "==3.8",
            VersionRange(
                min=Version(3, 8), max=Version(3, 8), include_min=True, include_max=True
            ),
        ),
        (
            "== 3.8",
            VersionRange(
                min=Version(3, 8), max=Version(3, 8), include_min=True, include_max=True
            ),
        ),
        (
            "~2.7 || ~3.8",
            VersionUnion(
                VersionRange(min=Version(2, 7), max=Version(2, 8), include_min=True),
                VersionRange(min=Version(3, 8), max=Version(3, 9), include_min=True),
            ),
        ),
        (
            "~2.7||~3.8",
            VersionUnion(
                VersionRange(min=Version(2, 7), max=Version(2, 8), include_min=True),
                VersionRange(min=Version(3, 8), max=Version(3, 9), include_min=True),
            ),
        ),
        (
            "~ 2.7||~ 3.8",
            VersionUnion(
                VersionRange(min=Version(2, 7), max=Version(2, 8), include_min=True),
                VersionRange(min=Version(3, 8), max=Version(3, 9), include_min=True),
            ),
        ),
    ],
)
def test_parse_constraint(constraint, version):
    assert parse_constraint(constraint) == version
