import pytest

from poetry.semver.comparison import compare
from poetry.semver.comparison import equal
from poetry.semver.comparison import greater_than
from poetry.semver.comparison import greater_than_or_equal
from poetry.semver.comparison import less_than
from poetry.semver.comparison import less_than_or_equal
from poetry.semver.comparison import not_equal


@pytest.mark.parametrize(
    'version1, version2, expected',
    [
        ('1.25.0', '1.24.0', True),
        ('1.25.0', '1.25.0', False),
        ('1.25.0', '1.26.0', False),
    ]
)
def test_greater_than(version1, version2, expected):
    if expected is True:
        assert greater_than(version1, version2)
    else:
        assert not greater_than(version1, version2)


@pytest.mark.parametrize(
    'version1, version2, expected',
    [
        ('1.25.0', '1.24.0', True),
        ('1.25.0', '1.25.0', True),
        ('1.25.0', '1.26.0', False),
    ]
)
def test_greater_than_or_equal(version1, version2, expected):
    if expected is True:
        assert greater_than_or_equal(version1, version2)
    else:
        assert not greater_than_or_equal(version1, version2)


@pytest.mark.parametrize(
    'version1, version2, expected',
    [
        ('1.25.0', '1.24.0', False),
        ('1.25.0', '1.25.0', False),
        ('1.25.0', '1.26.0', True),
        ('1.25.0', '1.26.0-beta', True),
        ('1.25.0', '1.25.0-beta', False),
    ]
)
def test_less_than(version1, version2, expected):
    if expected is True:
        assert less_than(version1, version2)
    else:
        assert not less_than(version1, version2)


@pytest.mark.parametrize(
    'version1, version2, expected',
    [
        ('1.25.0', '1.24.0', False),
        ('1.25.0', '1.25.0', True),
        ('1.25.0', '1.26.0', True),
    ]
)
def test_less_than_or_equal(version1, version2, expected):
    if expected is True:
        assert less_than_or_equal(version1, version2)
    else:
        assert not less_than_or_equal(version1, version2)


@pytest.mark.parametrize(
    'version1, version2, expected',
    [
        ('1.25.0', '1.24.0', False),
        ('1.25.0', '1.25.0', True),
        ('1.25.0', '1.26.0', False),
    ]
)
def test_equal(version1, version2, expected):
    if expected is True:
        assert equal(version1, version2)
    else:
        assert not equal(version1, version2)


@pytest.mark.parametrize(
    'version1, version2, expected',
    [
        ('1.25.0', '1.24.0', True),
        ('1.25.0', '1.25.0', False),
        ('1.25.0', '1.26.0', True),
    ]
)
def test_not_equal(version1, version2, expected):
    if expected is True:
        assert not_equal(version1, version2)
    else:
        assert not not_equal(version1, version2)


@pytest.mark.parametrize(
    'version1, operator, version2, expected',
    [
        ('1.25.0', '>', '1.24.0', True),
        ('1.25.0', '>', '1.25.0', False),
        ('1.25.0', '>', '1.26.0', False),
        ('1.25.0', '>=', '1.24.0', True),
        ('1.25.0', '>=', '1.25.0', True),
        ('1.25.0', '>=', '1.26.0', False),
        ('1.25.0', '<', '1.24.0', False),
        ('1.25.0', '<', '1.25.0', False),
        ('1.25.0', '<', '1.26.0', True),
        ('1.25.0-beta2.1', '<', '1.25.0-b.3', True),
        ('1.25.0-b2.1', '<', '1.25.0beta.3', True),
        ('1.25.0-b-2.1', '<', '1.25.0-rc', True),
        ('1.25.0', '<=', '1.24.0', False),
        ('1.25.0', '<=', '1.25.0', True),
        ('1.25.0', '<=', '1.26.0', True),
        ('1.25.0', '==', '1.24.0', False),
        ('1.25.0', '==', '1.25.0', True),
        ('1.25.0', '==', '1.26.0', False),
        ('1.25.0-beta2.1', '==', '1.25.0-b.2.1', True),
        ('1.25.0beta2.1', '==', '1.25.0-b2.1', True),
        ('1.25.0', '=', '1.24.0', False),
        ('1.25.0', '=', '1.25.0', True),
        ('1.25.0', '=', '1.26.0', False),
        ('1.25.0', '!=', '1.24.0', True),
        ('1.25.0', '!=', '1.25.0', False),
        ('1.25.0', '!=', '1.26.0', True),
    ]
)
def test_compare(version1, operator, version2, expected):
    if expected is True:
        assert compare(version1, operator, version2)
    else:
        assert not compare(version1, operator, version2)

