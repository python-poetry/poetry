from __future__ import annotations

from typing import TYPE_CHECKING

from cleo.io.null_io import NullIO
from packaging.utils import canonicalize_name
from poetry.core.packages.package import Package

from poetry.factory import Factory
from tests.helpers import get_package
from tests.mixology.helpers import add_to_repo
from tests.mixology.helpers import check_solver_result
from tests.mixology.version_solver.conftest import Provider


if TYPE_CHECKING:
    from poetry.core.packages.project_package import ProjectPackage

    from poetry.repositories import Repository
    from poetry.repositories import RepositoryPool


def test_with_compatible_locked_dependencies(
    root: ProjectPackage, repo: Repository, pool: RepositoryPool
):
    root.add_dependency(Factory.create_dependency("foo", "*"))

    add_to_repo(repo, "foo", "1.0.0", deps={"bar": "1.0.0"})
    add_to_repo(repo, "foo", "1.0.1", deps={"bar": "1.0.1"})
    add_to_repo(repo, "foo", "1.0.2", deps={"bar": "1.0.2"})
    add_to_repo(repo, "bar", "1.0.0")
    add_to_repo(repo, "bar", "1.0.1")
    add_to_repo(repo, "bar", "1.0.2")

    locked = [get_package("foo", "1.0.1"), get_package("bar", "1.0.1")]
    provider = Provider(root, pool, NullIO(), locked=locked)

    check_solver_result(
        root,
        provider,
        result={"foo": "1.0.1", "bar": "1.0.1"},
    )


def test_with_incompatible_locked_dependencies(
    root: ProjectPackage, repo: Repository, pool: RepositoryPool
):
    root.add_dependency(Factory.create_dependency("foo", ">1.0.1"))

    add_to_repo(repo, "foo", "1.0.0", deps={"bar": "1.0.0"})
    add_to_repo(repo, "foo", "1.0.1", deps={"bar": "1.0.1"})
    add_to_repo(repo, "foo", "1.0.2", deps={"bar": "1.0.2"})
    add_to_repo(repo, "bar", "1.0.0")
    add_to_repo(repo, "bar", "1.0.1")
    add_to_repo(repo, "bar", "1.0.2")

    locked = [get_package("foo", "1.0.1"), get_package("bar", "1.0.1")]
    provider = Provider(root, pool, NullIO(), locked=locked)

    check_solver_result(
        root,
        provider,
        result={"foo": "1.0.2", "bar": "1.0.2"},
    )


def test_with_unrelated_locked_dependencies(
    root: ProjectPackage, repo: Repository, pool: RepositoryPool
):
    root.add_dependency(Factory.create_dependency("foo", "*"))

    add_to_repo(repo, "foo", "1.0.0", deps={"bar": "1.0.0"})
    add_to_repo(repo, "foo", "1.0.1", deps={"bar": "1.0.1"})
    add_to_repo(repo, "foo", "1.0.2", deps={"bar": "1.0.2"})
    add_to_repo(repo, "bar", "1.0.0")
    add_to_repo(repo, "bar", "1.0.1")
    add_to_repo(repo, "bar", "1.0.2")
    add_to_repo(repo, "baz", "1.0.0")

    locked = [get_package("baz", "1.0.1")]
    provider = Provider(root, pool, NullIO(), locked=locked)

    check_solver_result(
        root,
        provider,
        result={"foo": "1.0.2", "bar": "1.0.2"},
    )


def test_unlocks_dependencies_if_necessary_to_ensure_that_a_new_dependency_is_satisfied(
    root: ProjectPackage, repo: Repository, pool: RepositoryPool
):
    root.add_dependency(Factory.create_dependency("foo", "*"))
    root.add_dependency(Factory.create_dependency("newdep", "2.0.0"))

    add_to_repo(repo, "foo", "1.0.0", deps={"bar": "<2.0.0"})
    add_to_repo(repo, "bar", "1.0.0", deps={"baz": "<2.0.0"})
    add_to_repo(repo, "baz", "1.0.0", deps={"qux": "<2.0.0"})
    add_to_repo(repo, "qux", "1.0.0")
    add_to_repo(repo, "foo", "2.0.0", deps={"bar": "<3.0.0"})
    add_to_repo(repo, "bar", "2.0.0", deps={"baz": "<3.0.0"})
    add_to_repo(repo, "baz", "2.0.0", deps={"qux": "<3.0.0"})
    add_to_repo(repo, "qux", "2.0.0")
    add_to_repo(repo, "newdep", "2.0.0", deps={"baz": ">=1.5.0"})

    locked = [
        get_package("foo", "2.0.0"),
        get_package("bar", "1.0.0"),
        get_package("baz", "1.0.0"),
        get_package("qux", "1.0.0"),
    ]
    provider = Provider(root, pool, NullIO(), locked=locked)

    check_solver_result(
        root,
        provider,
        result={
            "foo": "2.0.0",
            "bar": "2.0.0",
            "baz": "2.0.0",
            "qux": "1.0.0",
            "newdep": "2.0.0",
        },
    )


def test_with_compatible_locked_dependencies_use_latest(
    root: ProjectPackage, repo: Repository, pool: RepositoryPool
):
    root.add_dependency(Factory.create_dependency("foo", "*"))
    root.add_dependency(Factory.create_dependency("baz", "*"))

    add_to_repo(repo, "foo", "1.0.0", deps={"bar": "1.0.0"})
    add_to_repo(repo, "foo", "1.0.1", deps={"bar": "1.0.1"})
    add_to_repo(repo, "foo", "1.0.2", deps={"bar": "1.0.2"})
    add_to_repo(repo, "bar", "1.0.0")
    add_to_repo(repo, "bar", "1.0.1")
    add_to_repo(repo, "bar", "1.0.2")
    add_to_repo(repo, "baz", "1.0.0")
    add_to_repo(repo, "baz", "1.0.1")

    locked = [
        get_package("foo", "1.0.1"),
        get_package("bar", "1.0.1"),
        get_package("baz", "1.0.0"),
    ]
    provider = Provider(root, pool, NullIO(), locked=locked)

    check_solver_result(
        root,
        provider,
        result={"foo": "1.0.2", "bar": "1.0.2", "baz": "1.0.0"},
        use_latest=[canonicalize_name("foo")],
    )


def test_with_compatible_locked_dependencies_with_extras(
    root: ProjectPackage, repo: Repository, pool: RepositoryPool
):
    root.add_dependency(Factory.create_dependency("foo", "^1.0"))

    package_foo_0 = get_package("foo", "1.0.0")
    package_foo_1 = get_package("foo", "1.0.1")
    bar_extra_dep = Factory.create_dependency(
        "bar", {"version": "^1.0", "extras": "extra"}
    )
    for package_foo in (package_foo_0, package_foo_1):
        package_foo.add_dependency(bar_extra_dep)
        repo.add_package(package_foo)

    bar_deps = {"baz": {"version": "^1.0", "extras": ["extra"]}}
    add_to_repo(repo, "bar", "1.0.0", bar_deps)
    add_to_repo(repo, "bar", "1.0.1", bar_deps)
    add_to_repo(repo, "baz", "1.0.0")
    add_to_repo(repo, "baz", "1.0.1")

    locked = [
        get_package("foo", "1.0.0"),
        get_package("bar", "1.0.0"),
        get_package("baz", "1.0.0"),
    ]
    provider = Provider(root, pool, NullIO(), locked=locked)

    check_solver_result(
        root,
        provider,
        result={"foo": "1.0.0", "bar": "1.0.0", "baz": "1.0.0"},
    )


def test_with_yanked_package_in_lock(
    root: ProjectPackage, repo: Repository, pool: RepositoryPool
):
    root.add_dependency(Factory.create_dependency("foo", "*"))

    add_to_repo(repo, "foo", "1")
    add_to_repo(repo, "foo", "2", yanked=True)

    # yanked version is kept in lock file
    locked_foo = get_package("foo", "2")
    assert not locked_foo.yanked
    provider = Provider(root, pool, NullIO(), locked=[locked_foo])
    result = check_solver_result(
        root,
        provider,
        result={"foo": "2"},
    )
    foo = result.packages[0]
    assert foo.yanked

    # without considering the lock file, the other version is chosen
    provider = Provider(root, pool, NullIO())
    check_solver_result(
        root,
        provider,
        result={"foo": "1"},
    )


def test_no_update_is_respected_for_legacy_repository(
    root: ProjectPackage, repo: Repository, pool: RepositoryPool
):
    root.add_dependency(Factory.create_dependency("foo", "^1.0"))

    foo_100 = Package(
        "foo", "1.0.0", source_type="legacy", source_url="http://example.com"
    )
    foo_101 = Package(
        "foo", "1.0.1", source_type="legacy", source_url="http://example.com"
    )
    repo.add_package(foo_100)
    repo.add_package(foo_101)

    provider = Provider(root, pool, NullIO(), locked=[foo_100])
    check_solver_result(
        root,
        provider,
        result={"foo": "1.0.0"},
    )
