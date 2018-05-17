import pytest

from poetry.semver import parse_constraint
from poetry.semver import Version
from poetry.semver import VersionRange


@pytest.mark.parametrize(
    'input,constraint',
    [
        ('*', VersionRange()),
        ('*.*', VersionRange()),
        ('v*.*', VersionRange()),
        ('*.x.*', VersionRange()),
        ('x.X.x.*', VersionRange()),
        # ('!=1.0.0', Constraint('!=', '1.0.0.0')),
        ('>1.0.0', VersionRange(min=Version(1, 0, 0))),
        ('<1.2.3', VersionRange(max=Version(1, 2, 3))),
        ('<=1.2.3', VersionRange(max=Version(1, 2, 3), include_max=True)),
        ('>=1.2.3', VersionRange(min=Version(1, 2, 3), include_min=True)),
        ('=1.2.3', Version(1, 2, 3)),
        ('1.2.3', Version(1, 2, 3)),
        ('=1.0', Version(1, 0, 0)),
        ('1.2.3b5', Version(1, 2, 3, 'b5')),
        ('>= 1.2.3', VersionRange(min=Version(1, 2, 3), include_min=True))
    ]
)
def test_parse_constraint(input, constraint):
    assert parse_constraint(input) == constraint


@pytest.mark.parametrize(
    'input,constraint',
    [
        ('v2.*', VersionRange(Version(2, 0, 0), Version(3, 0, 0), True)),
        ('2.*.*', VersionRange(Version(2, 0, 0), Version(3, 0, 0), True)),
        ('20.*', VersionRange(Version(20, 0, 0), Version(21, 0, 0), True)),
        ('20.*.*', VersionRange(Version(20, 0, 0), Version(21, 0, 0), True)),
        ('2.0.*', VersionRange(Version(2, 0, 0), Version(2, 1, 0), True)),
        ('2.x', VersionRange(Version(2, 0, 0), Version(3, 0, 0), True)),
        ('2.x.x', VersionRange(Version(2, 0, 0), Version(3, 0, 0), True)),
        ('2.2.X', VersionRange(Version(2, 2, 0), Version(2, 3, 0), True)),
        ('0.*', VersionRange(max=Version(1, 0, 0))),
        ('0.*.*', VersionRange(max=Version(1, 0, 0))),
        ('0.x', VersionRange(max=Version(1, 0, 0))),
    ]
)
def test_parse_constraint_wildcard(input, constraint):
    assert parse_constraint(input) == constraint


@pytest.mark.parametrize(
    'input,constraint',
    [
        ('~v1', VersionRange(Version(1, 0, 0), Version(2, 0, 0), True)),
        ('~1.0', VersionRange(Version(1, 0, 0), Version(1, 1, 0), True)),
        ('~1.0.0', VersionRange(Version(1, 0, 0), Version(1, 1, 0), True)),
        ('~1.2', VersionRange(Version(1, 2, 0), Version(1, 3, 0), True)),
        ('~1.2.3', VersionRange(Version(1, 2, 3), Version(1, 3, 0), True)),
        ('~1.2-beta', VersionRange(Version(1, 2, 0, 'beta'), Version(1, 3, 0), True)),
        ('~1.2-b2', VersionRange(Version(1, 2, 0, 'b2'), Version(1, 3, 0), True)),
        ('~0.3', VersionRange(Version(0, 3, 0), Version(0, 4, 0), True)),
    ]
)
def test_parse_constraint_tilde(input, constraint):
    assert parse_constraint(input) == constraint


@pytest.mark.parametrize(
    'input,constraint',
    [
        ('^v1', VersionRange(Version(1, 0, 0), Version(2, 0, 0), True)),
        ('^0', VersionRange(Version(0, 0, 0), Version(1, 0, 0), True)),
        ('^0.0', VersionRange(Version(0, 0, 0), Version(0, 1, 0), True)),
        ('^1.2', VersionRange(Version(1, 2, 0), Version(2, 0, 0), True)),
        ('^1.2.3-beta.2', VersionRange(Version(1, 2, 3, 'beta.2'), Version(2, 0, 0), True)),
        ('^1.2.3', VersionRange(Version(1, 2, 3), Version(2, 0, 0), True)),
        ('^0.2.3', VersionRange(Version(0, 2, 3), Version(0, 3, 0), True)),
        ('^0.2', VersionRange(Version(0, 2, 0), Version(0, 3, 0), True)),
        ('^0.2.0', VersionRange(Version(0, 2, 0), Version(0, 3, 0), True)),
        ('^0.0.3', VersionRange(Version(0, 0, 3), Version(0, 0, 4), True)),
    ]
)
def test_parse_constraint_caret(input, constraint):
    assert parse_constraint(input) == constraint


@pytest.mark.parametrize(
    'input',
    [
        '>2.0,<=3.0',
        '>2.0 <=3.0',
        '>2.0  <=3.0',
        '>2.0, <=3.0',
        '>2.0 ,<=3.0',
        '>2.0 , <=3.0',
        '>2.0   , <=3.0',
        '> 2.0   <=  3.0',
        '> 2.0  ,  <=  3.0',
        '  > 2.0  ,  <=  3.0 ',
    ]
)
def test_parse_constraint_multi(input):
    assert parse_constraint(input) == VersionRange(
        Version(2, 0, 0), Version(3, 0, 0),
        include_min=False,
        include_max=True
    )


@pytest.mark.parametrize(
    'input,constraint',
    [
        ('!=v2.*', VersionRange(max=Version.parse('2.0')).union(VersionRange(Version.parse('3.0'), include_min=True))),
        ('!=2.*.*', VersionRange(max=Version.parse('2.0')).union(VersionRange(Version.parse('3.0'), include_min=True))),
        ('!=2.0.*', VersionRange(max=Version.parse('2.0')).union(VersionRange(Version.parse('2.1'), include_min=True))),
        ('!=0.*', VersionRange(Version.parse('1.0'), include_min=True)),
        ('!=0.*.*', VersionRange(Version.parse('1.0'), include_min=True)),
    ]
)
def test_parse_constraints_negative_wildcard(input, constraint):
    assert parse_constraint(input) == constraint
