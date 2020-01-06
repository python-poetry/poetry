import pytest

from poetry.semver import Version
from poetry.semver import VersionRange
from poetry.semver import VersionUnion
from poetry.semver import parse_constraint


@pytest.mark.parametrize(
    "input,constraint",
    [
        ("*", VersionRange()),
        ("*.*", VersionRange()),
        ("v*.*", VersionRange()),
        ("*.x.*", VersionRange()),
        ("x.X.x.*", VersionRange()),
        # ('!=1.0.0', Constraint('!=', '1.0.0.0')),
        (">1.0.0", VersionRange(min=Version(1, 0, 0))),
        ("<1.2.3", VersionRange(max=Version(1, 2, 3))),
        ("<=1.2.3", VersionRange(max=Version(1, 2, 3), include_max=True)),
        (">=1.2.3", VersionRange(min=Version(1, 2, 3), include_min=True)),
        ("=1.2.3", Version(1, 2, 3)),
        ("1.2.3", Version(1, 2, 3)),
        ("=1.0", Version(1, 0, 0)),
        ("1.2.3b5", Version(1, 2, 3, pre="b5")),
        (">= 1.2.3", VersionRange(min=Version(1, 2, 3), include_min=True)),
        (">dev", VersionRange(min=Version(0, 0, pre="dev"))),  # Issue 206
    ],
)
def test_parse_constraint(input, constraint):
    assert parse_constraint(input) == constraint


@pytest.mark.parametrize(
    "input,constraint",
    [
        ("v2.*", VersionRange(Version(2, 0, 0), Version(3, 0, 0), True)),
        ("2.*.*", VersionRange(Version(2, 0, 0), Version(3, 0, 0), True)),
        ("20.*", VersionRange(Version(20, 0, 0), Version(21, 0, 0), True)),
        ("20.*.*", VersionRange(Version(20, 0, 0), Version(21, 0, 0), True)),
        ("2.0.*", VersionRange(Version(2, 0, 0), Version(2, 1, 0), True)),
        ("2.x", VersionRange(Version(2, 0, 0), Version(3, 0, 0), True)),
        ("2.x.x", VersionRange(Version(2, 0, 0), Version(3, 0, 0), True)),
        ("2.2.X", VersionRange(Version(2, 2, 0), Version(2, 3, 0), True)),
        ("0.*", VersionRange(max=Version(1, 0, 0))),
        ("0.*.*", VersionRange(max=Version(1, 0, 0))),
        ("0.x", VersionRange(max=Version(1, 0, 0))),
    ],
)
def test_parse_constraint_wildcard(input, constraint):
    assert parse_constraint(input) == constraint


@pytest.mark.parametrize(
    "input,constraint",
    [
        ("~v1", VersionRange(Version(1, 0, 0), Version(2, 0, 0), True)),
        ("~1.0", VersionRange(Version(1, 0, 0), Version(1, 1, 0), True)),
        ("~1.0.0", VersionRange(Version(1, 0, 0), Version(1, 1, 0), True)),
        ("~1.2", VersionRange(Version(1, 2, 0), Version(1, 3, 0), True)),
        ("~1.2.3", VersionRange(Version(1, 2, 3), Version(1, 3, 0), True)),
        (
            "~1.2-beta",
            VersionRange(Version(1, 2, 0, pre="beta"), Version(1, 3, 0), True),
        ),
        ("~1.2-b2", VersionRange(Version(1, 2, 0, pre="b2"), Version(1, 3, 0), True)),
        ("~0.3", VersionRange(Version(0, 3, 0), Version(0, 4, 0), True)),
        ("~3.5", VersionRange(Version(3, 5, 0), Version(3, 6, 0), True)),
        ("~=3.5", VersionRange(Version(3, 5, 0), Version(4, 0, 0), True)),  # PEP 440
        ("~=3.5.3", VersionRange(Version(3, 5, 3), Version(3, 6, 0), True)),  # PEP 440
        (
            "~=3.5.3rc1",
            VersionRange(Version(3, 5, 3, pre="rc1"), Version(3, 6, 0), True),
        ),  # PEP 440
    ],
)
def test_parse_constraint_tilde(input, constraint):
    assert parse_constraint(input) == constraint


@pytest.mark.parametrize(
    "input,constraint",
    [
        ("^v1", VersionRange(Version(1, 0, 0), Version(2, 0, 0), True)),
        ("^0", VersionRange(Version(0, 0, 0), Version(1, 0, 0), True)),
        ("^0.0", VersionRange(Version(0, 0, 0), Version(0, 1, 0), True)),
        ("^1.2", VersionRange(Version(1, 2, 0), Version(2, 0, 0), True)),
        (
            "^1.2.3-beta.2",
            VersionRange(Version(1, 2, 3, pre="beta.2"), Version(2, 0, 0), True),
        ),
        ("^1.2.3", VersionRange(Version(1, 2, 3), Version(2, 0, 0), True)),
        ("^0.2.3", VersionRange(Version(0, 2, 3), Version(0, 3, 0), True)),
        ("^0.2", VersionRange(Version(0, 2, 0), Version(0, 3, 0), True)),
        ("^0.2.0", VersionRange(Version(0, 2, 0), Version(0, 3, 0), True)),
        ("^0.0.3", VersionRange(Version(0, 0, 3), Version(0, 0, 4), True)),
    ],
)
def test_parse_constraint_caret(input, constraint):
    assert parse_constraint(input) == constraint


@pytest.mark.parametrize(
    "input",
    [
        ">2.0,<=3.0",
        ">2.0 <=3.0",
        ">2.0  <=3.0",
        ">2.0, <=3.0",
        ">2.0 ,<=3.0",
        ">2.0 , <=3.0",
        ">2.0   , <=3.0",
        "> 2.0   <=  3.0",
        "> 2.0  ,  <=  3.0",
        "  > 2.0  ,  <=  3.0 ",
    ],
)
def test_parse_constraint_multi(input):
    assert parse_constraint(input) == VersionRange(
        Version(2, 0, 0), Version(3, 0, 0), include_min=False, include_max=True
    )


@pytest.mark.parametrize(
    "input",
    [">=2.7,!=3.0.*,!=3.1.*", ">=2.7, !=3.0.*, !=3.1.*", ">= 2.7, != 3.0.*, != 3.1.*"],
)
def test_parse_constraint_multi_wilcard(input):
    assert parse_constraint(input) == VersionUnion(
        VersionRange(Version(2, 7, 0), Version(3, 0, 0), True, False),
        VersionRange(Version(3, 2, 0), None, True, False),
    )


@pytest.mark.parametrize(
    "input,constraint",
    [
        (
            "!=v2.*",
            VersionRange(max=Version.parse("2.0")).union(
                VersionRange(Version.parse("3.0"), include_min=True)
            ),
        ),
        (
            "!=2.*.*",
            VersionRange(max=Version.parse("2.0")).union(
                VersionRange(Version.parse("3.0"), include_min=True)
            ),
        ),
        (
            "!=2.0.*",
            VersionRange(max=Version.parse("2.0")).union(
                VersionRange(Version.parse("2.1"), include_min=True)
            ),
        ),
        ("!=0.*", VersionRange(Version.parse("1.0"), include_min=True)),
        ("!=0.*.*", VersionRange(Version.parse("1.0"), include_min=True)),
    ],
)
def test_parse_constraints_negative_wildcard(input, constraint):
    assert parse_constraint(input) == constraint


@pytest.mark.parametrize(
    "input, expected",
    [
        ("1", "1"),
        ("1.2", "1.2"),
        ("1.2.3", "1.2.3"),
        ("!=1", "!=1"),
        ("!=1.2", "!=1.2"),
        ("!=1.2.3", "!=1.2.3"),
        ("^1", ">=1,<2"),
        ("^1.0", ">=1.0,<2.0"),
        ("^1.0.0", ">=1.0.0,<2.0.0"),
        ("~1", ">=1,<2"),
        ("~1.0", ">=1.0,<1.1"),
        ("~1.0.0", ">=1.0.0,<1.1.0"),
    ],
)
def test_constraints_keep_version_precision(input, expected):
    assert str(parse_constraint(input)) == expected


@pytest.mark.parametrize(
    "unsorted, sorted_",
    [
        (["1.0.3", "1.0.2", "1.0.1"], ["1.0.1", "1.0.2", "1.0.3"]),
        (["1.0.0.2", "1.0.0.0rc2"], ["1.0.0.0rc2", "1.0.0.2"]),
        (["1.0.0.0", "1.0.0.0rc2"], ["1.0.0.0rc2", "1.0.0.0"]),
        (["1.0.0.0.0", "1.0.0.0rc2"], ["1.0.0.0rc2", "1.0.0.0.0"]),
        (["1.0.0rc2", "1.0.0rc1"], ["1.0.0rc1", "1.0.0rc2"]),
        (["1.0.0rc2", "1.0.0b1"], ["1.0.0b1", "1.0.0rc2"]),
    ],
)
def test_versions_are_sortable(unsorted, sorted_):
    unsorted = [parse_constraint(u) for u in unsorted]
    sorted_ = [parse_constraint(s) for s in sorted_]

    assert sorted(unsorted) == sorted_
