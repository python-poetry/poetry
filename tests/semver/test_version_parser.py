import pytest

from poetry.semver.version_parser import VersionParser
from poetry.semver.constraints.constraint import Constraint
from poetry.semver.constraints.empty_constraint import EmptyConstraint
from poetry.semver.constraints.multi_constraint import MultiConstraint


@pytest.fixture
def parser():
    return VersionParser()


@pytest.mark.parametrize(
    'input,constraint',
    [
        ('*', EmptyConstraint()),
        ('*.*', EmptyConstraint()),
        ('v*.*', EmptyConstraint()),
        ('*.x.*', EmptyConstraint()),
        ('x.X.x.*', EmptyConstraint()),
        ('!=1.0.0', Constraint('!=', '1.0.0.0')),
        ('>1.0.0', Constraint('>', '1.0.0.0')),
        ('<1.2.3.4', Constraint('<', '1.2.3.4')),
        ('<=1.2.3', Constraint('<=', '1.2.3.0')),
        ('>=1.2.3', Constraint('>=', '1.2.3.0')),
        ('=1.2.3', Constraint('=', '1.2.3.0')),
        ('1.2.3', Constraint('=', '1.2.3.0')),
        ('=1.0', Constraint('=', '1.0.0.0')),
        ('1.2.3b5', Constraint('=', '1.2.3.0-beta.5')),
        ('>= 1.2.3', Constraint('>=', '1.2.3.0'))
    ]
)
def test_parse_constraints_simple(parser, input, constraint):
    assert str(parser.parse_constraints(input)) == str(constraint)


@pytest.mark.parametrize(
    'input,min,max',
    [
        ('v2.*', Constraint('>=', '2.0.0.0'), Constraint('<', '3.0.0.0')),
        ('2.*.*', Constraint('>=', '2.0.0.0'), Constraint('<', '3.0.0.0')),
        ('20.*', Constraint('>=', '20.0.0.0'), Constraint('<', '21.0.0.0')),
        ('20.*.*', Constraint('>=', '20.0.0.0'), Constraint('<', '21.0.0.0')),
        ('2.0.*', Constraint('>=', '2.0.0.0'), Constraint('<', '2.1.0.0')),
        ('2.x', Constraint('>=', '2.0.0.0'), Constraint('<', '3.0.0.0')),
        ('2.x.x', Constraint('>=', '2.0.0.0'), Constraint('<', '3.0.0.0')),
        ('2.2.X', Constraint('>=', '2.2.0.0'), Constraint('<', '2.3.0.0')),
        ('0.*', None, Constraint('<', '1.0.0.0')),
        ('0.*.*', None, Constraint('<', '1.0.0.0')),
        ('0.x', None, Constraint('<', '1.0.0.0')),
    ]
)
def test_parse_constraints_wildcard(parser, input, min, max):
    if min:
        expected = MultiConstraint((min, max))
    else:
        expected = max

    assert str(parser.parse_constraints(input)) == str(expected)


@pytest.mark.parametrize(
    'input,min,max',
    [
        ('~v1', Constraint('>=', '1.0.0.0'), Constraint('<', '2.0.0.0')),
        ('~1.0', Constraint('>=', '1.0.0.0'), Constraint('<', '1.1.0.0')),
        ('~1.0.0', Constraint('>=', '1.0.0.0'), Constraint('<', '1.1.0.0')),
        ('~1.2', Constraint('>=', '1.2.0.0'), Constraint('<', '1.3.0.0')),
        ('~1.2.3', Constraint('>=', '1.2.3.0'), Constraint('<', '1.3.0.0')),
        ('~1.2.3.4', Constraint('>=', '1.2.3.4'), Constraint('<', '1.2.4.0')),
        ('~1.2-beta', Constraint('>=', '1.2.0.0-beta'), Constraint('<', '1.3.0.0')),
        ('~1.2-b2', Constraint('>=', '1.2.0.0-beta.2'), Constraint('<', '1.3.0.0')),
        ('~0.3', Constraint('>=', '0.3.0.0'), Constraint('<', '0.4.0.0')),
    ]
)
def test_parse_constraints_tilde(parser, input, min, max):
    if min:
        expected = MultiConstraint((min, max))
    else:
        expected = max

    assert str(parser.parse_constraints(input)) == str(expected)


@pytest.mark.parametrize(
    'input,min,max',
    [
        ('^v1', Constraint('>=', '1.0.0.0'), Constraint('<', '2.0.0.0')),
        ('^0', Constraint('>=', '0.0.0.0'), Constraint('<', '1.0.0.0')),
        ('^0.0', Constraint('>=', '0.0.0.0'), Constraint('<', '0.1.0.0')),
        ('^1.2', Constraint('>=', '1.2.0.0'), Constraint('<', '2.0.0.0')),
        ('^1.2.3-beta.2', Constraint('>=', '1.2.3.0-beta.2'), Constraint('<', '2.0.0.0')),
        ('^1.2.3.4', Constraint('>=', '1.2.3.4'), Constraint('<', '2.0.0.0')),
        ('^1.2.3', Constraint('>=', '1.2.3.0'), Constraint('<', '2.0.0.0')),
        ('^0.2.3', Constraint('>=', '0.2.3.0'), Constraint('<', '0.3.0.0')),
        ('^0.2', Constraint('>=', '0.2.0.0'), Constraint('<', '0.3.0.0')),
        ('^0.2.0', Constraint('>=', '0.2.0.0'), Constraint('<', '0.3.0.0')),
        ('^0.0.3', Constraint('>=', '0.0.3.0'), Constraint('<', '0.0.4.0')),
    ]
)
def test_parse_constraints_caret(parser, input, min, max):
    if min:
        expected = MultiConstraint((min, max))
    else:
        expected = max

    assert str(parser.parse_constraints(input)) == str(expected)


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
def test_parse_constraints_multi(parser, input):
    first = Constraint('>', '2.0.0.0')
    second = Constraint('<=', '3.0.0.0')
    multi = MultiConstraint((first, second))

    assert str(parser.parse_constraints(input)) == str(multi)


@pytest.mark.parametrize(
    'input',
    [
        '>2.0,<2.0.5 | >2.0.6',
        '>2.0,<2.0.5 || >2.0.6',
        '> 2.0 , <2.0.5 | >  2.0.6',
    ]
)
def test_parse_constraints_multi2(parser, input):
    first = Constraint('>', '2.0.0.0')
    second = Constraint('<', '2.0.5.0')
    third = Constraint('>', '2.0.6.0')
    multi1 = MultiConstraint((first, second))
    multi2 = MultiConstraint((multi1, third), False)

    assert str(parser.parse_constraints(input)) == str(multi2)


@pytest.mark.parametrize(
    'input',
    [
        '',
        '1.0.0-meh',
        '>2.0,,<=3.0',
        '>2.0 ,, <=3.0',
        '>2.0 ||| <=3.0',
    ]
)
def test_parse_constraints_fail(parser, input):
    with pytest.raises(ValueError):
        parser.parse_constraints(input)
