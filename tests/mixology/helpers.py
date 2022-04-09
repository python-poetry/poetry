from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.core.packages.package import Package

from poetry.factory import Factory
from poetry.mixology.failure import SolveFailure
from poetry.mixology.version_solver import VersionSolver
from poetry.packages import DependencyPackage


if TYPE_CHECKING:
    from poetry.packages.project_package import ProjectPackage
    from poetry.repositories import Repository
    from tests.mixology.version_solver.conftest import Provider


def add_to_repo(
    repository: Repository,
    name: str,
    version: str,
    deps: dict[str, str] | None = None,
    python: str | None = None,
) -> None:
    package = Package(name, version)
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
    locked: dict[str, Package] | None = None,
    use_latest: list[str] | None = None,
) -> None:
    if locked is not None:
        locked = {
            k: [DependencyPackage(l.to_dependency(), l)] for k, l in locked.items()
        }

    solver = VersionSolver(root, provider, locked=locked, use_latest=use_latest)
    try:
        solution = solver.solve()
    except SolveFailure as e:
        if error:
            assert str(e) == error

            if tries is not None:
                assert solver.solution.attempted_solutions == tries

            return

        raise
    except AssertionError as e:
        if error:
            assert str(e) == error
            return
        raise

    packages = {}
    for package in solution.packages:
        packages[package.name] = str(package.version)

    assert result == packages

    if tries is not None:
        assert solution.attempted_solutions == tries
