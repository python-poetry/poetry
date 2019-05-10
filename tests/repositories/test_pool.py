import pytest

from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.repositories.exceptions import PackageNotFound


def test_pool_raises_package_not_found_when_no_package_is_found():
    pool = Pool()
    pool.add_repository(Repository())

    with pytest.raises(PackageNotFound):
        pool.package("foo", "1.0.0")


def test_pool():
    pool = Pool()

    assert 0 == len(pool.repositories)
    assert pool.default is None


def test_pool_with_initial_repositories():
    repo = Repository()
    pool = Pool([repo])

    assert 1 == len(pool.repositories)
    assert pool.default is None
