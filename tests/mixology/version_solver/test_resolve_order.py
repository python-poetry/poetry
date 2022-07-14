from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.factory import Factory
from tests.mixology.helpers import add_to_repo
from tests.mixology.helpers import check_solver_result


if TYPE_CHECKING:
    from poetry.core.packages.project_package import ProjectPackage

    from poetry.repositories import Repository
    from tests.mixology.version_solver.conftest import Provider


def test_solver_prefer_packages_with_as_few_versions_as_possible(
    root: ProjectPackage, provider: Provider, repo: Repository
):
    root.add_dependency(Factory.create_dependency("foo", "*"))
    root.add_dependency(Factory.create_dependency("bar", "*"))

    add_to_repo(repo, "foo", "1.0", deps={"bar": "1.1"})
    add_to_repo(repo, "foo", "1.1", deps={"bar": "1.0"})
    add_to_repo(repo, "foo", "1.2", deps={"bar": "1.0"})
    add_to_repo(repo, "foo", "1.3", deps={"bar": "1.0"})
    add_to_repo(repo, "foo", "1.4", deps={"bar": "1.0"})

    add_to_repo(repo, "bar", "1.0")
    add_to_repo(repo, "bar", "1.1")

    check_solver_result(root, provider, {"foo": "1.0", "bar": "1.1"})


def test_solver_respects_resolve_order(
    root: ProjectPackage, provider: Provider, repo: Repository
):
    root.add_dependency(Factory.create_dependency("foo", {"version": "*", "resolve-order": 1}))
    root.add_dependency(Factory.create_dependency("bar", "*"))

    add_to_repo(repo, "foo", "1.0", deps={"bar": "1.1"})
    add_to_repo(repo, "foo", "1.1", deps={"bar": "1.0"})
    add_to_repo(repo, "foo", "1.2", deps={"bar": "1.0"})
    add_to_repo(repo, "foo", "1.3", deps={"bar": "1.0"})
    add_to_repo(repo, "foo", "1.4", deps={"bar": "1.0"})

    add_to_repo(repo, "bar", "1.0")
    add_to_repo(repo, "bar", "1.1")

    check_solver_result(root, provider, {"foo": "1.4", "bar": "1.0"})
