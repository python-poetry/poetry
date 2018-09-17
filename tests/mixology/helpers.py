from poetry.packages import DependencyPackage
from poetry.packages import Package
from poetry.mixology.failure import SolveFailure
from poetry.mixology.version_solver import VersionSolver


def add_to_repo(repository, name, version, deps=None, python=None):
    package = Package(name, version)
    if python:
        package.python_versions = python

    if deps:
        for dep_name, dep_constraint in deps.items():
            package.add_dependency(dep_name, dep_constraint)

    repository.add_package(package)


def check_solver_result(
    root, provider, result=None, error=None, tries=None, locked=None, use_latest=None
):
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
