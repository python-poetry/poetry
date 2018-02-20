from poetry.semver.constraints.constraint import Constraint
from poetry.semver.constraints.multi_constraint import MultiConstraint


def test_multi_version_match_succeeds():
    require_start = Constraint('>', '1.0')
    require_end = Constraint('<', '1.2')
    provider = Constraint('==', '1.1')

    multi = MultiConstraint((require_start, require_end))

    assert multi.matches(provider)


def test_multi_version_provided_match_succeeds():
    require_start = Constraint('>', '1.0')
    require_end = Constraint('<', '1.2')
    provide_start = Constraint('>=', '1.1')
    provide_end = Constraint('<', '2.0')

    multi_require = MultiConstraint((require_start, require_end))
    multi_provide = MultiConstraint((provide_start, provide_end))

    assert multi_require.matches(multi_provide)


def test_multi_version_match_fails():
    require_start = Constraint('>', '1.0')
    require_end = Constraint('<', '1.2')
    provider = Constraint('==', '1.2')

    multi = MultiConstraint((require_start, require_end))

    assert not multi.matches(provider)
