import pytest

from poetry.semver.constraints.constraint import Constraint


@pytest.mark.parametrize(
    'require_op, require_version, provide_op, provide_version',
    [
        ('==', '1', '==', '1'),
        ('>=', '1', '>=', '2'),
        ('>=', '2', '>=', '1'),
        ('>=', '2', '>', '1'),
        ('<=', '2', '>=', '1'),
        ('>=', '1', '<=', '2'),
        ('==', '2', '>=', '2'),
        ('!=', '1', '!=', '1'),
        ('!=', '1', '==', '2'),
        ('!=', '1', '<', '1'),
        ('!=', '1', '<=', '1'),
        ('!=', '1', '>', '1'),
        ('!=', '1', '>=', '1')
    ]
)
def test_version_match_succeeds(require_op, require_version,
                                provide_op, provide_version):
    require = Constraint(require_op, require_version)
    provide = Constraint(provide_op, provide_version)

    assert require.matches(provide)


@pytest.mark.parametrize(
    'require_op, require_version, provide_op, provide_version',
    [
        ('==', '1', '==', '2'),
        ('>=', '2', '<=', '1'),
        ('>=', '2', '<', '2'),
        ('<=', '2', '>', '2'),
        ('>', '2', '<=', '2'),
        ('<=', '1', '>=', '2'),
        ('>=', '2', '<=', '1'),
        ('==', '2', '<', '2'),
        ('!=', '1', '==', '1'),
        ('==', '1', '!=', '1'),
    ]
)
def test_version_match_fails(require_op, require_version,
                             provide_op, provide_version):
    require = Constraint(require_op, require_version)
    provide = Constraint(provide_op, provide_version)

    assert not require.matches(provide)


def test_invalid_operators():
    with pytest.raises(ValueError):
        Constraint('invalid', '1.2.3')
