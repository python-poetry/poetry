from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.core.packages.package import Package

from poetry.factory import Factory
from poetry.mixology.failure import SolveFailure
from poetry.mixology.version_solver import VersionSolver


if TYPE_CHECKING:
    from collections.abc import Mapping

    from packaging.utils import NormalizedName
    from poetry.core.factory import DependencyConstraint
    from poetry.core.packages.project_package import ProjectPackage

    from poetry.mixology.result import SolverResult
    from poetry.repositories import Repository
    from tests.mixology.version_solver.conftest import Provider


def add_to_repo(
    repository: Repository,
    name: str,
    version: str,
    deps: Mapping[str, DependencyConstraint] | None = None,
    python: str | None = None,
    yanked: bool = False,
) -> None:
    package = Package(name, version, yanked=yanked)
    if python:
        package.python_versions = python

    if deps:
        for dep_name, dep_constraint in deps.items():
            package.add_dependency(Factory.create_dependency(dep_name, dep_constraint))

    repository.add_package(package)


def check_solver_result(
    root: ProjectPackage,
    provider: Provider,
    result: dict[str, str] | None = None,
    error: str | None = None,
    tries: int | None = None,
    use_latest: list[NormalizedName] | None = None,
) -> SolverResult | None:
    solver = VersionSolver(root, provider)
    with provider.use_latest_for(use_latest or []):
        try:
            solution = solver.solve()
        except SolveFailure as e:
            if error:
                assert str(e) == error

                if tries is not None:
                    assert solver.solution.attempted_solutions == tries

            return None

        except AssertionError as e:
            if error:
                assert str(e) == error
                return None
            raise

    packages = {}
    for package in solution.packages:
        packages[package.name] = str(package.version)

    assert packages == result

    if tries is not None:
        assert solution.attempted_solutions == tries

    return solution
