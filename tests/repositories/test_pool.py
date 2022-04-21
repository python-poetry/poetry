from __future__ import annotations

from unittest.mock import Mock

import pytest

from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.core.packages.dependency import Dependency


def test_pool_raises_package_not_found_when_no_package_is_found():
    pool = Pool()
    pool.add_repository(Repository())

    with pytest.raises(PackageNotFound):
        pool.package("foo", "1.0.0")


def test_pool():
    pool = Pool()

    assert len(pool.repositories) == 0
    assert not pool.has_default()


def test_pool_with_initial_repositories():
    repo = Repository()
    pool = Pool([repo])

    assert len(pool.repositories) == 1
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


def test_find_packages_do_not_call_secondary_if_primary_find_package():
    secondary = LegacyRepository("secondary", "https://secondary.com", secondary=True)
    repo2 = LegacyRepository("bar", "https://bar.baz")

    pool = Pool()
    pool.add_repository(secondary, secondary=True)
    pool.add_repository(repo2)

    dependency = Dependency("test", "1.0.0")

    repo2.find_packages = Mock(return_value=["t"])
    secondary.find_packages = Mock(return_value=["t"])
    pool.find_packages(dependency)
    repo2.find_packages.assert_called_once_with(dependency)
    secondary.find_packages.assert_not_called()


def test_find_packages_call_secondary_if_primary_do_not_find_package():
    secondary = LegacyRepository("secondary", "https://secondary.com", secondary=True)
    repo2 = LegacyRepository("bar", "https://bar.baz")

    pool = Pool()
    pool.add_repository(secondary, secondary=True)
    pool.add_repository(repo2)

    dependency = Dependency("test", "1.0.0")

    repo2.find_packages = Mock(return_value=[])
    secondary.find_packages = Mock(return_value=["t"])
    pool.find_packages(dependency)
    repo2.find_packages.assert_called_once_with(dependency)
    secondary.find_packages.assert_called_once_with(dependency)
