from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.factory import Factory
from tests.mixology.helpers import add_to_repo
from tests.mixology.helpers import check_solver_result


if TYPE_CHECKING:
    from poetry.core.packages.project_package import ProjectPackage

    from poetry.repositories import Repository
    from tests.mixology.version_solver.conftest import Provider


def test_circular_dependency_on_older_version(
    root: ProjectPackage, provider: Provider, repo: Repository
):
    root.add_dependency(Factory.create_dependency("a", ">=1.0.0"))

    add_to_repo(repo, "a", "1.0.0")
    add_to_repo(repo, "a", "2.0.0", deps={"b": "1.0.0"})
    add_to_repo(repo, "b", "1.0.0", deps={"a": "1.0.0"})

    check_solver_result(root, provider, {"a": "1.0.0"}, tries=2)


def test_diamond_dependency_graph(
    root: ProjectPackage, provider: Provider, repo: Repository
):
    root.add_dependency(Factory.create_dependency("a", "*"))
    root.add_dependency(Factory.create_dependency("b", "*"))

    add_to_repo(repo, "a", "2.0.0", deps={"c": "^1.0.0"})
    add_to_repo(repo, "a", "1.0.0")

    add_to_repo(repo, "b", "2.0.0", deps={"c": "^3.0.0"})
    add_to_repo(repo, "b", "1.0.0", deps={"c": "^2.0.0"})

    add_to_repo(repo, "c", "3.0.0")
    add_to_repo(repo, "c", "2.0.0")
    add_to_repo(repo, "c", "1.0.0")

    check_solver_result(root, provider, {"a": "1.0.0", "b": "2.0.0", "c": "3.0.0"})


def test_backjumps_after_partial_satisfier(
    root: ProjectPackage, provider: Provider, repo: Repository
):
    # c 2.0.0 is incompatible with y 2.0.0 because it requires x 1.0.0, but that
    # requirement only exists because of both a and b. The solver should be able
    # to deduce c 2.0.0's incompatibility and select c 1.0.0 instead.
    root.add_dependency(Factory.create_dependency("c", "*"))
    root.add_dependency(Factory.create_dependency("y", "^2.0.0"))

    add_to_repo(repo, "a", "1.0.0", deps={"x": ">=1.0.0"})
    add_to_repo(repo, "b", "1.0.0", deps={"x": "<2.0.0"})

    add_to_repo(repo, "c", "1.0.0")
    add_to_repo(repo, "c", "2.0.0", deps={"a": "*", "b": "*"})

    add_to_repo(repo, "x", "0.0.0")
    add_to_repo(repo, "x", "1.0.0", deps={"y": "1.0.0"})
    add_to_repo(repo, "x", "2.0.0")

    add_to_repo(repo, "y", "1.0.0")
    add_to_repo(repo, "y", "2.0.0")

    check_solver_result(root, provider, {"c": "1.0.0", "y": "2.0.0"}, tries=2)


def test_rolls_back_leaf_versions_first(
    root: ProjectPackage, provider: Provider, repo: Repository
):
    # The latest versions of a and b disagree on c. An older version of either
    # will resolve the problem. This test validates that b, which is farther
    # in the dependency graph from myapp is downgraded first.
    root.add_dependency(Factory.create_dependency("a", "*"))

    add_to_repo(repo, "a", "1.0.0", deps={"b": "*"})
    add_to_repo(repo, "a", "2.0.0", deps={"b": "*", "c": "2.0.0"})
    add_to_repo(repo, "b", "1.0.0")
    add_to_repo(repo, "b", "2.0.0", deps={"c": "1.0.0"})
    add_to_repo(repo, "c", "1.0.0")
    add_to_repo(repo, "c", "2.0.0")

    check_solver_result(root, provider, {"a": "2.0.0", "b": "1.0.0", "c": "2.0.0"})


def test_simple_transitive(root: ProjectPackage, provider: Provider, repo: Repository):
    # Only one version of baz, so foo and bar will have to downgrade
    # until they reach it
    root.add_dependency(Factory.create_dependency("foo", "*"))

    add_to_repo(repo, "foo", "1.0.0", deps={"bar": "1.0.0"})
    add_to_repo(repo, "foo", "2.0.0", deps={"bar": "2.0.0"})
    add_to_repo(repo, "foo", "3.0.0", deps={"bar": "3.0.0"})

    add_to_repo(repo, "bar", "1.0.0", deps={"baz": "*"})
    add_to_repo(repo, "bar", "2.0.0", deps={"baz": "2.0.0"})
    add_to_repo(repo, "bar", "3.0.0", deps={"baz": "3.0.0"})

    add_to_repo(repo, "baz", "1.0.0")

    check_solver_result(
        root, provider, {"foo": "1.0.0", "bar": "1.0.0", "baz": "1.0.0"}, tries=3
    )


def test_backjump_to_nearer_unsatisfied_package(
    root: ProjectPackage, provider: Provider, repo: Repository
):
    # This ensures it doesn't exhaustively search all versions of b when it's
    # a-2.0.0 whose dependency on c-2.0.0-nonexistent led to the problem. We
    # make sure b has more versions than a so that the solver tries a first
    # since it sorts sibling dependencies by number of versions.
    root.add_dependency(Factory.create_dependency("a", "*"))
    root.add_dependency(Factory.create_dependency("b", "*"))

    add_to_repo(repo, "a", "1.0.0", deps={"c": "1.0.0"})
    add_to_repo(repo, "a", "2.0.0", deps={"c": "2.0.0-1"})
    add_to_repo(repo, "b", "1.0.0")
    add_to_repo(repo, "b", "2.0.0")
    add_to_repo(repo, "b", "3.0.0")
    add_to_repo(repo, "c", "1.0.0")

    check_solver_result(
        root, provider, {"a": "1.0.0", "b": "3.0.0", "c": "1.0.0"}, tries=2
    )


def test_traverse_into_package_with_fewer_versions_first(
    root: ProjectPackage, provider: Provider, repo: Repository
):
    # Dependencies are ordered so that packages with fewer versions are tried
    # first. Here, there are two valid solutions (either a or b must be
    # downgraded once). The chosen one depends on which dep is traversed first.
    # Since b has fewer versions, it will be traversed first, which means a will
    # come later. Since later selections are revised first, a gets downgraded.
    root.add_dependency(Factory.create_dependency("a", "*"))
    root.add_dependency(Factory.create_dependency("b", "*"))

    add_to_repo(repo, "a", "1.0.0", deps={"c": "*"})
    add_to_repo(repo, "a", "2.0.0", deps={"c": "*"})
    add_to_repo(repo, "a", "3.0.0", deps={"c": "*"})
    add_to_repo(repo, "a", "4.0.0", deps={"c": "*"})
    add_to_repo(repo, "a", "5.0.0", deps={"c": "1.0.0"})
    add_to_repo(repo, "b", "1.0.0", deps={"c": "*"})
    add_to_repo(repo, "b", "2.0.0", deps={"c": "*"})
    add_to_repo(repo, "b", "3.0.0", deps={"c": "*"})
    add_to_repo(repo, "b", "4.0.0", deps={"c": "2.0.0"})
    add_to_repo(repo, "c", "1.0.0")
    add_to_repo(repo, "c", "2.0.0")

    check_solver_result(root, provider, {"a": "4.0.0", "b": "4.0.0", "c": "2.0.0"})


def test_backjump_past_failed_package_on_disjoint_constraint(
    root: ProjectPackage, provider: Provider, repo: Repository
):
    root.add_dependency(Factory.create_dependency("a", "*"))
    root.add_dependency(Factory.create_dependency("foo", ">2.0.0"))

    add_to_repo(repo, "a", "1.0.0", deps={"foo": "*"})  # ok
    add_to_repo(
        repo, "a", "2.0.0", deps={"foo": "<1.0.0"}
    )  # disjoint with myapp's constraint on foo

    add_to_repo(repo, "foo", "2.0.0")
    add_to_repo(repo, "foo", "2.0.1")
    add_to_repo(repo, "foo", "2.0.2")
    add_to_repo(repo, "foo", "2.0.3")
    add_to_repo(repo, "foo", "2.0.4")

    check_solver_result(root, provider, {"a": "1.0.0", "foo": "2.0.4"})
