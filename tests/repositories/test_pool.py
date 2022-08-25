from __future__ import annotations

import pytest

from poetry.core.semver.version import Version

from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.legacy_repository import LegacyRepository


def test_pool_raises_package_not_found_when_no_package_is_found() -> None:
    pool = Pool()
    pool.add_repository(Repository("repo"))

    with pytest.raises(PackageNotFound):
        pool.package("foo", Version.parse("1.0.0"))


def test_pool():
    pool = Pool()

    assert len(pool.repositories) == 0
    assert not pool.has_default()


def test_pool_with_initial_repositories():
    repo = Repository("repo")
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


def test_remove_repository():
    repo1 = LegacyRepository("foo", "https://foo.bar")
    repo2 = LegacyRepository("bar", "https://bar.baz")
    repo3 = LegacyRepository("baz", "https://baz.quux")

    pool = Pool()
    pool.add_repository(repo1)
    pool.add_repository(repo2)
    pool.add_repository(repo3)
    pool.remove_repository("bar")

    assert pool.repository("foo") is repo1
    assert not pool.has_repository("bar")
    assert pool.repository("baz") is repo3


def test_remove_default_repository():
    default = LegacyRepository("default", "https://default.com")
    repo1 = LegacyRepository("foo", "https://foo.bar")
    repo2 = LegacyRepository("bar", "https://bar.baz")
    new_default = LegacyRepository("new_default", "https://new.default.com")

    pool = Pool()
    pool.add_repository(repo1)
    pool.add_repository(repo2)
    pool.add_repository(default, default=True)

    assert pool.has_default()

    pool.remove_repository("default")

    assert not pool.has_default()

    pool.add_repository(new_default, default=True)

    assert pool.has_default()
    assert pool.repositories[0] is new_default
    assert not pool.has_repository("default")


def test_repository_ordering():
    default1 = LegacyRepository("default1", "https://default1.com")
    default2 = LegacyRepository("default2", "https://default2.com")
    primary1 = LegacyRepository("primary1", "https://primary1.com")
    primary2 = LegacyRepository("primary2", "https://primary2.com")
    primary3 = LegacyRepository("primary3", "https://primary3.com")
    secondary1 = LegacyRepository("secondary1", "https://secondary1.com")
    secondary2 = LegacyRepository("secondary2", "https://secondary2.com")
    secondary3 = LegacyRepository("secondary3", "https://secondary3.com")

    pool = Pool()
    pool.add_repository(secondary1, secondary=True)
    pool.add_repository(primary1)
    pool.add_repository(default1, default=True)
    pool.add_repository(primary2)
    pool.add_repository(secondary2, secondary=True)

    pool.remove_repository("primary2")
    pool.remove_repository("secondary2")

    pool.add_repository(primary3)
    pool.add_repository(secondary3, secondary=True)

    assert pool.repositories == [default1, primary1, primary3, secondary1, secondary3]
    with pytest.raises(ValueError):
        pool.add_repository(default2, default=True)
