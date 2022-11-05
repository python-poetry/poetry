from __future__ import annotations

import pytest

from poetry.core.constraints.version import Version

from poetry.repositories import Repository
from poetry.repositories import RepositoryPool
from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.legacy_repository import LegacyRepository
from tests.helpers import get_dependency
from tests.helpers import get_package


def test_pool() -> None:
    pool = RepositoryPool()

    assert len(pool.repositories) == 0
    assert not pool.has_default()
    assert not pool.has_primary_repositories()


def test_pool_with_initial_repositories() -> None:
    repo = Repository("repo")
    pool = RepositoryPool([repo])

    assert len(pool.repositories) == 1
    assert not pool.has_default()
    assert pool.has_primary_repositories()


def test_repository_no_repository() -> None:
    pool = RepositoryPool()

    with pytest.raises(IndexError):
        pool.repository("foo")


def test_adding_repositories_with_same_name_twice_raises_value_error() -> None:
    repo1 = Repository("repo")
    repo2 = Repository("repo")

    with pytest.raises(ValueError):
        RepositoryPool([repo1, repo2])

    with pytest.raises(ValueError):
        RepositoryPool([repo1]).add_repository(repo2)


def test_repository_from_normal_pool() -> None:
    repo = LegacyRepository("foo", "https://foo.bar")
    pool = RepositoryPool()
    pool.add_repository(repo)

    assert pool.repository("foo") is repo


def test_repository_from_secondary_pool() -> None:
    repo = LegacyRepository("foo", "https://foo.bar")
    pool = RepositoryPool()
    pool.add_repository(repo, secondary=True)

    assert pool.repository("foo") is repo


def test_repository_with_normal_default_and_secondary_repositories() -> None:
    secondary = LegacyRepository("secondary", "https://secondary.com")
    default = LegacyRepository("default", "https://default.com")
    repo1 = LegacyRepository("foo", "https://foo.bar")
    repo2 = LegacyRepository("bar", "https://bar.baz")

    pool = RepositoryPool()
    pool.add_repository(repo1)
    pool.add_repository(secondary, secondary=True)
    pool.add_repository(repo2)
    pool.add_repository(default, default=True)

    assert pool.repository("secondary") is secondary
    assert pool.repository("default") is default
    assert pool.repository("foo") is repo1
    assert pool.repository("bar") is repo2
    assert pool.has_default()
    assert pool.has_primary_repositories()


def test_remove_non_existing_repository_raises_indexerror() -> None:
    pool = RepositoryPool()

    with pytest.raises(IndexError):
        pool.remove_repository("foo")


def test_remove_existing_repository_successful() -> None:
    repo1 = LegacyRepository("foo", "https://foo.bar")
    repo2 = LegacyRepository("bar", "https://bar.baz")
    repo3 = LegacyRepository("baz", "https://baz.quux")

    pool = RepositoryPool()
    pool.add_repository(repo1)
    pool.add_repository(repo2)
    pool.add_repository(repo3)
    pool.remove_repository("bar")

    assert pool.repository("foo") is repo1
    assert not pool.has_repository("bar")
    assert pool.repository("baz") is repo3


def test_remove_default_repository() -> None:
    default = LegacyRepository("default", "https://default.com")
    repo1 = LegacyRepository("foo", "https://foo.bar")
    repo2 = LegacyRepository("bar", "https://bar.baz")
    new_default = LegacyRepository("new_default", "https://new.default.com")

    pool = RepositoryPool()
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


def test_repository_ordering() -> None:
    default1 = LegacyRepository("default1", "https://default1.com")
    default2 = LegacyRepository("default2", "https://default2.com")
    primary1 = LegacyRepository("primary1", "https://primary1.com")
    primary2 = LegacyRepository("primary2", "https://primary2.com")
    primary3 = LegacyRepository("primary3", "https://primary3.com")
    secondary1 = LegacyRepository("secondary1", "https://secondary1.com")
    secondary2 = LegacyRepository("secondary2", "https://secondary2.com")
    secondary3 = LegacyRepository("secondary3", "https://secondary3.com")

    pool = RepositoryPool()
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


def test_pool_get_package_in_any_repository() -> None:
    package1 = get_package("foo", "1.0.0")
    repo1 = Repository("repo1", [package1])
    package2 = get_package("bar", "1.0.0")
    repo2 = Repository("repo2", [package1, package2])
    pool = RepositoryPool([repo1, repo2])

    returned_package1 = pool.package("foo", Version.parse("1.0.0"))
    returned_package2 = pool.package("bar", Version.parse("1.0.0"))

    assert returned_package1 == package1
    assert returned_package2 == package2


def test_pool_get_package_in_specified_repository() -> None:
    package = get_package("foo", "1.0.0")
    repo1 = Repository("repo1")
    repo2 = Repository("repo2", [package])
    pool = RepositoryPool([repo1, repo2])

    returned_package = pool.package(
        "foo", Version.parse("1.0.0"), repository_name="repo2"
    )

    assert returned_package == package


def test_pool_no_package_from_any_repository_raises_package_not_found() -> None:
    pool = RepositoryPool()
    pool.add_repository(Repository("repo"))

    with pytest.raises(PackageNotFound):
        pool.package("foo", Version.parse("1.0.0"))


def test_pool_no_package_from_specified_repository_raises_package_not_found() -> None:
    package = get_package("foo", "1.0.0")
    repo1 = Repository("repo1")
    repo2 = Repository("repo2", [package])
    pool = RepositoryPool([repo1, repo2])

    with pytest.raises(PackageNotFound):
        pool.package("foo", Version.parse("1.0.0"), repository_name="repo1")


def test_pool_find_packages_in_any_repository() -> None:
    package1 = get_package("foo", "1.1.1")
    package2 = get_package("foo", "1.2.3")
    package3 = get_package("foo", "2.0.0")
    package4 = get_package("bar", "1.2.3")
    repo1 = Repository("repo1", [package1, package3])
    repo2 = Repository("repo2", [package1, package2, package4])
    pool = RepositoryPool([repo1, repo2])

    available_dependency = get_dependency("foo", "^1.0.0")
    returned_packages_available = pool.find_packages(available_dependency)
    unavailable_dependency = get_dependency("foo", "999.9.9")
    returned_packages_unavailable = pool.find_packages(unavailable_dependency)

    assert returned_packages_available == [package1, package1, package2]
    assert returned_packages_unavailable == []


def test_pool_find_packages_in_specified_repository() -> None:
    package_foo1 = get_package("foo", "1.1.1")
    package_foo2 = get_package("foo", "1.2.3")
    package_foo3 = get_package("foo", "2.0.0")
    package_bar = get_package("bar", "1.2.3")
    repo1 = Repository("repo1", [package_foo1, package_foo3])
    repo2 = Repository("repo2", [package_foo1, package_foo2, package_bar])
    pool = RepositoryPool([repo1, repo2])

    available_dependency = get_dependency("foo", "^1.0.0")
    available_dependency.source_name = "repo2"
    returned_packages_available = pool.find_packages(available_dependency)
    unavailable_dependency = get_dependency("foo", "999.9.9")
    unavailable_dependency.source_name = "repo2"
    returned_packages_unavailable = pool.find_packages(unavailable_dependency)

    assert returned_packages_available == [package_foo1, package_foo2]
    assert returned_packages_unavailable == []


def test_search_no_legacy_repositories() -> None:
    package_foo1 = get_package("foo", "1.0.0")
    package_foo2 = get_package("foo", "2.0.0")
    package_foobar = get_package("foobar", "1.0.0")
    repo1 = Repository("repo1", [package_foo1, package_foo2])
    repo2 = Repository("repo2", [package_foo1, package_foobar])
    pool = RepositoryPool([repo1, repo2])

    assert pool.search("foo") == [
        package_foo1,
        package_foo2,
        package_foo1,
        package_foobar,
    ]
    assert pool.search("bar") == [package_foobar]
    assert pool.search("nothing") == []


def test_search_legacy_repositories_are_skipped() -> None:
    package = get_package("foo", "1.0.0")
    repo1 = Repository("repo1", [package])
    repo2 = LegacyRepository("repo2", "https://fake.repo/")
    pool = RepositoryPool([repo1, repo2])

    assert pool.search("foo") == [package]
