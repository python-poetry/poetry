from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.factory import Factory
from tests.mixology.helpers import add_to_repo
from tests.mixology.helpers import check_solver_result


if TYPE_CHECKING:
    from poetry.core.packages.project_package import ProjectPackage

    from poetry.repositories import Repository
    from tests.mixology.version_solver.conftest import Provider


def test_simple_dependencies(
    root: ProjectPackage, provider: Provider, repo: Repository
):
    root.add_dependency(Factory.create_dependency("a", "1.0.0"))
    root.add_dependency(Factory.create_dependency("b", "1.0.0"))

    add_to_repo(repo, "a", "1.0.0", deps={"aa": "1.0.0", "ab": "1.0.0"})
    add_to_repo(repo, "b", "1.0.0", deps={"ba": "1.0.0", "bb": "1.0.0"})
    add_to_repo(repo, "aa", "1.0.0")
    add_to_repo(repo, "ab", "1.0.0")
    add_to_repo(repo, "ba", "1.0.0")
    add_to_repo(repo, "bb", "1.0.0")

    check_solver_result(
        root,
        provider,
        {
            "a": "1.0.0",
            "aa": "1.0.0",
            "ab": "1.0.0",
            "b": "1.0.0",
            "ba": "1.0.0",
            "bb": "1.0.0",
        },
    )


def test_shared_dependencies_with_overlapping_constraints(
    root: ProjectPackage, provider: Provider, repo: Repository
):
    root.add_dependency(Factory.create_dependency("a", "1.0.0"))
    root.add_dependency(Factory.create_dependency("b", "1.0.0"))

    add_to_repo(repo, "a", "1.0.0", deps={"shared": ">=2.0.0 <4.0.0"})
    add_to_repo(repo, "b", "1.0.0", deps={"shared": ">=3.0.0 <5.0.0"})
    add_to_repo(repo, "shared", "2.0.0")
    add_to_repo(repo, "shared", "3.0.0")
    add_to_repo(repo, "shared", "3.6.9")
    add_to_repo(repo, "shared", "4.0.0")
    add_to_repo(repo, "shared", "5.0.0")

    check_solver_result(root, provider, {"a": "1.0.0", "b": "1.0.0", "shared": "3.6.9"})


def test_shared_dependency_where_dependent_version_affects_other_dependencies(
    root: ProjectPackage, provider: Provider, repo: Repository
):
    root.add_dependency(Factory.create_dependency("foo", "<=1.0.2"))
    root.add_dependency(Factory.create_dependency("bar", "1.0.0"))

    add_to_repo(repo, "foo", "1.0.0")
    add_to_repo(repo, "foo", "1.0.1", deps={"bang": "1.0.0"})
    add_to_repo(repo, "foo", "1.0.2", deps={"whoop": "1.0.0"})
    add_to_repo(repo, "foo", "1.0.3", deps={"zoop": "1.0.0"})
    add_to_repo(repo, "bar", "1.0.0", deps={"foo": "<=1.0.1"})
    add_to_repo(repo, "bang", "1.0.0")
    add_to_repo(repo, "whoop", "1.0.0")
    add_to_repo(repo, "zoop", "1.0.0")

    check_solver_result(
        root, provider, {"foo": "1.0.1", "bar": "1.0.0", "bang": "1.0.0"}
    )


def test_circular_dependency(
    root: ProjectPackage, provider: Provider, repo: Repository
):
    root.add_dependency(Factory.create_dependency("foo", "1.0.0"))

    add_to_repo(repo, "foo", "1.0.0", deps={"bar": "1.0.0"})
    add_to_repo(repo, "bar", "1.0.0", deps={"foo": "1.0.0"})

    check_solver_result(root, provider, {"foo": "1.0.0", "bar": "1.0.0"})


@pytest.mark.parametrize(
    "constraint, versions, yanked_versions, expected",
    [
        (">=1", ["1", "2"], [], "2"),
        (">=1", ["1", "2"], ["2"], "1"),
        (">=1", ["1", "2", "3"], ["2"], "3"),
        (">=1", ["1", "2", "3"], ["2", "3"], "1"),
        (">1", ["1", "2"], ["2"], "error"),
        (">1", ["2"], ["2"], "error"),
        (">=2", ["2"], ["2"], "error"),
        ("==2", ["2"], ["2"], "2"),
        ("==2", ["2", "2+local"], [], "2+local"),
        ("==2", ["2", "2+local"], ["2+local"], "2"),
    ],
)
def test_yanked_release(
    root: ProjectPackage,
    provider: Provider,
    repo: Repository,
    constraint: str,
    versions: list[str],
    yanked_versions: list[str],
    expected: str,
) -> None:
    root.add_dependency(Factory.create_dependency("foo", constraint))

    for version in versions:
        add_to_repo(repo, "foo", version, yanked=version in yanked_versions)

    if expected == "error":
        result = None
        error = (
            f"Because myapp depends on foo ({constraint}) which doesn't match any "
            "versions, version solving failed."
        )
    else:
        result = {"foo": expected}
        error = None
    check_solver_result(root, provider, result, error)
