import pytest

from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.legacy_repository import LegacyRepository


def test_pool_raises_package_not_found_when_no_package_is_found():
    pool = Pool()
    pool.add_repository(Repository())

    with pytest.raises(PackageNotFound):
        pool.package("foo", "1.0.0")


def test_pool():
    pool = Pool()

    assert 0 == len(pool.repositories)
    assert not pool.has_default()


def test_pool_with_initial_repositories():
    repo = Repository()
    pool = Pool([repo])

    assert 1 == len(pool.repositories)
    assert not pool.has_default()


def test_repository_no_repository():
    pool = Pool()

    with pytest.raises(ValueError):
        pool.repository("foo")


def test_repository_from_normal_pool():
    repo = LegacyRepository("foo", "https://foo.bar")
    pool = Pool()
    pool.add_repository(repo)

    assert pool.repository("foo") is repo


def test_repository_from_secondary_pool():
    repo = LegacyRepository("foo", "https://foo.bar")
    pool = Pool()
    pool.add_repository(repo, secondary=True)

    assert pool.repository("foo") is repo


def test_repository_with_normal_default_and_secondary_repositories():
    secondary = LegacyRepository("secondary", "https://secondary.com")
    default = LegacyRepository("default", "https://default.com")
    repo1 = LegacyRepository("foo", "https://foo.bar")
    repo2 = LegacyRepository("bar", "https://bar.baz")

    pool = Pool()
    pool.add_repository(repo1)
    pool.add_repository(secondary, secondary=True)
    pool.add_repository(repo2)
    pool.add_repository(default, default=True)

    assert pool.repository("secondary") is secondary
    assert pool.repository("default") is default
    assert pool.repository("foo") is repo1
    assert pool.repository("bar") is repo2
    assert pool.has_default()
