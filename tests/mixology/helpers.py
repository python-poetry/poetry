from typing import TYPE_CHECKING
from typing import Dict
from typing import List
from typing import Optional

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
    repository: "Repository",
    name: str,
    version: str,
    deps: Optional[Dict[str, str]] = None,
    python: Optional[str] = None,
) -> None:
    package = Package(name, version)
    if python:
        package.python_versions = python

    if deps:
        for dep_name, dep_constraint in deps.items():
            package.add_dependency(Factory.create_dependency(dep_name, dep_constraint))

    repository.add_package(package)


def check_solver_result(
    root: "ProjectPackage",
    provider: "Provider",
    result: Optional[Dict[str, str]] = None,
    error: Optional[str] = None,
    tries: Optional[int] = None,
    locked: Optional[Dict[str, Package]] = None,
    use_latest: Optional[List[str]] = None,
) -> None:
    if locked is not None:
        locked = {k: DependencyPackage(l.to_dependency(), l) for k, l in locked.items()}

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

    packages = {}
    for package in solution.packages:
        packages[package.name] = str(package.version)

    assert result == packages

    if tries is not None:
        assert solution.attempted_solutions == tries
