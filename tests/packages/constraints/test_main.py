import pytest

from poetry.packages.constraints import parse_constraint
from poetry.packages.constraints.any_constraint import AnyConstraint
from poetry.packages.constraints.constraint import Constraint
from poetry.packages.constraints.multi_constraint import MultiConstraint
from poetry.packages.constraints.union_constraint import UnionConstraint


@pytest.mark.parametrize(
    "input,constraint",
    [
        ("*", AnyConstraint()),
        ("win32", Constraint("win32", "=")),
        ("=win32", Constraint("win32", "=")),
        ("==win32", Constraint("win32", "=")),
        ("!=win32", Constraint("win32", "!=")),
        ("!= win32", Constraint("win32", "!=")),
    ],
)
def test_parse_constraint(input, constraint):
    assert parse_constraint(input) == constraint


@pytest.mark.parametrize(
    "input,constraint",
    [
        (
            "!=win32,!=linux",
            MultiConstraint(Constraint("win32", "!="), Constraint("linux", "!=")),
        ),
        (
            "!=win32,!=linux,!=linux2",
            MultiConstraint(
                Constraint("win32", "!="),
                Constraint("linux", "!="),
                Constraint("linux2", "!="),
            ),
        ),
    ],
)
def test_parse_constraint_multi(input, constraint):
    assert parse_constraint(input) == constraint


@pytest.mark.parametrize(
    "input,constraint",
    [
        ("win32 || linux", UnionConstraint(Constraint("win32"), Constraint("linux"))),
        (
            "win32 || !=linux2",
            UnionConstraint(Constraint("win32"), Constraint("linux2", "!=")),
        ),
    ],
)
def test_parse_constraint_multi(input, constraint):
    assert parse_constraint(input) == constraint
