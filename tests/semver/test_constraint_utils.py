import pytest

import poetry.semver
from poetry.semver.constraint_utils import is_constraint
from poetry.semver.constraint_utils import sorted_constraints

# TODO: test PEP-0440 vs. SEM-VER constraints


# from test_main.py
@pytest.mark.parametrize(
    "constraint,result",
    [
        ("*", True),
        ("*.*", True),
        ("v*.*", True),
        ("*.x.*", True),
        ("x.X.x.*", True),
        ("!=1.0.0", True),
        (">1.0.0", True),
        ("<1.2.3", True),
        ("<=1.2.3", True),
        (">=1.2.3", True),
        ("=1.2.3", True),
        ("1.2.3", True),
        ("=1.0", True),
        ("1.2.3b5", True),
        (">= 1.2.3", True),
        (">dev", True),
        ("n.a.n", False),
        ("hot-fix-666", False),
    ],
)
def test_is_constraint(mocker, constraint, result):
    # the full responsibility for validating all constraints lies with parse_single_constraint,
    # this test just checks that it is called within `is_constraint` for a few examples.
    parser = mocker.spy(poetry.semver.constraint_utils, name="parse_single_constraint")
    assert is_constraint(constraint) == result
    assert parser.call_count == 1


@pytest.mark.parametrize(
    "unsorted, sorted_",
    [
        ([">1.2.3", "<=1.2.3"], ["<=1.2.3", ">1.2.3"]),
        (["1.0.3", "1.0.2", "1.0.1"], ["1.0.1", "1.0.2", "1.0.3"]),
        (
            ["1.0.3", "1.0.2", "1.0.1", "n.a.n", "hot-fix-666"],
            ["1.0.1", "1.0.2", "1.0.3"],
        ),
        (["10.0.3", "1.0.3", "n.a.n", "hot-fix-666"], ["1.0.3", "10.0.3"]),
    ],
)
def test_sorted_constraints(mocker, unsorted, sorted_):
    parser = mocker.spy(poetry.semver.constraint_utils, name="parse_single_constraint")
    assert sorted_constraints(unsorted) == sorted_
    # parser is called to (a) check is_constraint and (b) instantiate VersionConstraint for sort key
    assert parser.call_count == (len(unsorted) + len(sorted_))
    # test the reverse order
    parser.reset_mock()
    assert sorted_constraints(unsorted, reverse=True) == list(reversed(sorted_))
    assert parser.call_count == (len(unsorted) + len(sorted_))
