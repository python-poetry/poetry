from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.factory import Factory
from poetry.puzzle.provider import IncompatibleConstraintsError
from tests.mixology.helpers import add_to_repo
from tests.mixology.helpers import check_solver_result


if TYPE_CHECKING:
    from poetry.core.packages.project_package import ProjectPackage

    from poetry.repositories import Repository
    from tests.mixology.version_solver.conftest import Provider
    from tests.types import FixtureDirGetter


def test_no_version_matching_constraint(
    root: ProjectPackage, provider: Provider, repo: Repository
) -> None:
    root.add_dependency(Factory.create_dependency("foo", "^1.0"))

    add_to_repo(repo, "foo", "2.0.0")
    add_to_repo(repo, "foo", "2.1.3")

    check_solver_result(
        root,
        provider,
        error=(
            "Because myapp depends on foo (^1.0) "
            "which doesn't match any versions, version solving failed."
        ),
    )


def test_no_version_that_matches_combined_constraints(
    root: ProjectPackage, provider: Provider, repo: Repository
) -> None:
    root.add_dependency(Factory.create_dependency("foo", "1.0.0"))
    root.add_dependency(Factory.create_dependency("bar", "1.0.0"))

    add_to_repo(repo, "foo", "1.0.0", deps={"shared": ">=2.0.0 <3.0.0"})
    add_to_repo(repo, "bar", "1.0.0", deps={"shared": ">=2.9.0 <4.0.0"})
    add_to_repo(repo, "shared", "2.5.0")
    add_to_repo(repo, "shared", "3.5.0")

    error = """\
Because foo (1.0.0) depends on shared (>=2.0.0 <3.0.0)
 and no versions of shared match >=2.9.0,<3.0.0,\
 foo (1.0.0) requires shared (>=2.0.0,<2.9.0).
And because bar (1.0.0) depends on shared (>=2.9.0 <4.0.0),\
 bar (1.0.0) is incompatible with foo (1.0.0).
So, because myapp depends on both foo (1.0.0) and bar (1.0.0), version solving failed.\
"""

    check_solver_result(root, provider, error=error)


def test_disjoint_constraints(
    root: ProjectPackage, provider: Provider, repo: Repository
) -> None:
    root.add_dependency(Factory.create_dependency("foo", "1.0.0"))
    root.add_dependency(Factory.create_dependency("bar", "1.0.0"))

    add_to_repo(repo, "foo", "1.0.0", deps={"shared": "<=2.0.0"})
    add_to_repo(repo, "bar", "1.0.0", deps={"shared": ">3.0.0"})
    add_to_repo(repo, "shared", "2.0.0")
    add_to_repo(repo, "shared", "4.0.0")

    error = """\
Because bar (1.0.0) depends on shared (>3.0.0)
 and foo (1.0.0) depends on shared (<=2.0.0),\
 bar (1.0.0) is incompatible with foo (1.0.0).
So, because myapp depends on both foo (1.0.0) and bar (1.0.0), version solving failed.\
"""

    check_solver_result(root, provider, error=error)
    check_solver_result(root, provider, error=error)


def test_disjoint_root_constraints(
    root: ProjectPackage, provider: Provider, repo: Repository
) -> None:
    root.add_dependency(Factory.create_dependency("foo", "1.0.0"))
    root.add_dependency(Factory.create_dependency("foo", "2.0.0"))

    add_to_repo(repo, "foo", "1.0.0")
    add_to_repo(repo, "foo", "2.0.0")

    error = """\
Incompatible constraints in requirements of myapp (0.0.0):
foo (==1.0.0)
foo (==2.0.0)"""

    with pytest.raises(IncompatibleConstraintsError) as e:
        check_solver_result(root, provider, error=error)

    assert str(e.value) == error


def test_disjoint_root_constraints_path_dependencies(
    root: ProjectPackage,
    provider: Provider,
    repo: Repository,
    fixture_dir: FixtureDirGetter,
) -> None:
    provider.set_package_python_versions("^3.7")
    project_dir = fixture_dir("with_conditional_path_deps")
    dependency1 = Factory.create_dependency("demo", {"path": project_dir / "demo_one"})
    root.add_dependency(dependency1)
    dependency2 = Factory.create_dependency("demo", {"path": project_dir / "demo_two"})
    root.add_dependency(dependency2)

    error = f"""\
Incompatible constraints in requirements of myapp (0.0.0):
demo @ {project_dir.as_uri()}/demo_two (1.2.3)
demo @ {project_dir.as_uri()}/demo_one (1.2.3)"""

    with pytest.raises(IncompatibleConstraintsError) as e:
        check_solver_result(root, provider, error=error)

    assert str(e.value) == error


def test_no_valid_solution(
    root: ProjectPackage, provider: Provider, repo: Repository
) -> None:
    root.add_dependency(Factory.create_dependency("a", "*"))
    root.add_dependency(Factory.create_dependency("b", "*"))

    add_to_repo(repo, "a", "1.0.0", deps={"b": "1.0.0"})
    add_to_repo(repo, "a", "2.0.0", deps={"b": "2.0.0"})

    add_to_repo(repo, "b", "1.0.0", deps={"a": "2.0.0"})
    add_to_repo(repo, "b", "2.0.0", deps={"a": "1.0.0"})

    error = """\
Because no versions of b match <1.0.0 || >1.0.0,<2.0.0 || >2.0.0
 and b (1.0.0) depends on a (2.0.0), b (!=2.0.0) requires a (2.0.0).
And because a (2.0.0) depends on b (2.0.0), b is forbidden.
Because b (2.0.0) depends on a (1.0.0) which depends on b (1.0.0), b is forbidden.
Thus, b is forbidden.
So, because myapp depends on b (*), version solving failed."""

    check_solver_result(root, provider, error=error, tries=2)


def test_package_with_the_same_name_gives_clear_error_message(
    root: ProjectPackage, provider: Provider, repo: Repository
) -> None:
    pkg_name = "a"
    root.add_dependency(Factory.create_dependency(pkg_name, "*"))
    add_to_repo(repo, pkg_name, "1.0.0", deps={pkg_name: "1.0.0"})
    error = f"Package '{pkg_name}' is listed as a dependency of itself."
    check_solver_result(root, provider, error=error)
