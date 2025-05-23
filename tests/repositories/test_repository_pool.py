from __future__ import annotations

import pytest

from poetry.core.constraints.version import Version

from poetry.repositories import Repository
from poetry.repositories import RepositoryPool
from poetry.repositories.exceptions import PackageNotFoundError
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.repository_pool import Priority
from tests.helpers import get_dependency
from tests.helpers import get_package


def test_pool() -> None:
    pool = RepositoryPool()

    assert len(pool.repositories) == 0
    assert not pool.has_primary_repositories()


def test_pool_with_initial_repositories() -> None:
    repo = Repository("repo")
    pool = RepositoryPool([repo])

    assert len(pool.repositories) == 1
    assert pool.has_primary_repositories()
    assert pool.get_priority("repo") == Priority.PRIMARY


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


@pytest.mark.parametrize("priority", (p for p in Priority))
def test_repository_from_single_repo_pool(priority: Priority) -> None:
    repo = LegacyRepository("foo", "https://foo.bar")
    pool = RepositoryPool()

    pool.add_repository(repo, priority=priority)

    assert pool.repository("foo") is repo
    assert pool.get_priority("foo") == priority


def test_repository_with_all_prio_repositories() -> None:
    supplemental = LegacyRepository("supplemental", "https://supplemental.com")
    repo1 = LegacyRepository("foo", "https://foo.bar")
    repo2 = LegacyRepository("bar", "https://bar.baz")
    explicit = LegacyRepository("explicit", "https://bar.baz")

    pool = RepositoryPool()
    pool.add_repository(repo1)
    pool.add_repository(repo2)
    pool.add_repository(supplemental, priority=Priority.SUPPLEMENTAL)
    pool.add_repository(explicit, priority=Priority.EXPLICIT)

    assert pool.repository("foo") is repo1
    assert pool.repository("bar") is repo2
    assert pool.repository("supplemental") is supplemental
    assert pool.repository("explicit") is explicit
    assert pool.has_primary_repositories()


def test_repository_supplemental_repositories_do_show() -> None:
    supplemental = LegacyRepository("supplemental", "https://supplemental.com")

    pool = RepositoryPool()
    pool.add_repository(supplemental, priority=Priority.SUPPLEMENTAL)

    assert pool.repository("supplemental") is supplemental
    assert pool.repositories == [supplemental]


def test_repository_explicit_repositories_do_not_show() -> None:
    explicit = LegacyRepository("explicit", "https://explicit.com")
    primary = LegacyRepository("primary", "https://primary.com")

    pool = RepositoryPool()
    pool.add_repository(explicit, priority=Priority.EXPLICIT)
    pool.add_repository(primary, priority=Priority.PRIMARY)

    assert pool.repository("explicit") is explicit
    assert pool.repository("primary") is primary
    assert pool.repositories == [primary]
    assert pool.all_repositories == [primary, explicit]


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


def test_repository_ordering() -> None:
    primary1 = LegacyRepository("primary1", "https://primary1.com")
    primary2 = LegacyRepository("primary2", "https://primary2.com")
    primary3 = LegacyRepository("primary3", "https://primary3.com")
    supplemental = LegacyRepository("supplemental", "https://supplemental.com")

    pool = RepositoryPool()
    pool.add_repository(supplemental, priority=Priority.SUPPLEMENTAL)
    pool.add_repository(primary1)
    pool.add_repository(primary2)

    pool.remove_repository("primary2")

    pool.add_repository(primary3)

    assert pool.repositories == [
        primary1,
        primary3,
        supplemental,
    ]


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


def test_pool_find_packages_only_considers_supplemental_when_needed() -> None:
    package1 = get_package("foo", "1.1.1")
    package2 = get_package("foo", "1.2.3")
    package3 = get_package("foo", "2.0.0")
    repo1 = Repository("repo1", [package1, package3])
    repo2 = Repository("repo2", [package1, package2])
    pool = RepositoryPool([repo1]).add_repository(repo2, priority=Priority.SUPPLEMENTAL)

    dependency_in_nonsupplemental = get_dependency("foo", "^1.0.0")
    returned_packages_in_nonsupplemental = pool.find_packages(
        dependency_in_nonsupplemental
    )
    dependency_needs_supplemental = get_dependency("foo", "1.2.3")
    returned_packages_needs_supplemental = pool.find_packages(
        dependency_needs_supplemental
    )

    assert returned_packages_in_nonsupplemental == [package1]
    assert returned_packages_needs_supplemental == [package2]


def test_pool_get_package_in_specified_repository() -> None:
    package = get_package("foo", "1.0.0")
    repo1 = Repository("repo1", [package])
    repo2 = Repository("repo2", [package])
    pool = RepositoryPool([repo1]).add_repository(repo2, priority=Priority.SUPPLEMENTAL)

    returned_package = pool.package(
        "foo", Version.parse("1.0.0"), repository_name="repo2"
    )

    assert returned_package == package


def test_pool_no_package_from_any_repository_raises_package_not_found() -> None:
    pool = RepositoryPool()
    pool.add_repository(Repository("repo"))

    with pytest.raises(PackageNotFoundError):
        pool.package("foo", Version.parse("1.0.0"))


def test_pool_no_package_from_specified_repository_raises_package_not_found() -> None:
    package = get_package("foo", "1.0.0")
    repo1 = Repository("repo1")
    repo2 = Repository("repo2", [package])
    pool = RepositoryPool([repo1, repo2])

    with pytest.raises(PackageNotFoundError):
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


def test_search_legacy_repositories_are_not_skipped(
    legacy_repository: LegacyRepository,
) -> None:
    foo_package = get_package("foo", "1.0.0")
    demo_package = get_package("demo", "0.1.0")

    repo1 = Repository("repo1", [foo_package])
    repo2 = legacy_repository
    pool = RepositoryPool([repo1, repo2])

    assert pool.search("foo") == [foo_package]

    assert repo1.search("demo") == []
    assert repo2.search("demo") == pool.search("demo") == [demo_package]
