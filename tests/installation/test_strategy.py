import pytest

from poetry.installation import Strategy


@pytest.mark.parametrize("strategy", ["lowest", Strategy.LOWEST])
def test_is_using_lowest_true(strategy):
    assert Strategy.is_using_lowest(strategy)


@pytest.mark.parametrize("strategy", ["latest", Strategy.LATEST])
def test_is_using_lowest_false(strategy):
    assert not Strategy.is_using_lowest(strategy)
