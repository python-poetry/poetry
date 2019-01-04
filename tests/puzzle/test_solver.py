import pytest

from cleo.outputs.null_output import NullOutput
from cleo.styles import OutputStyle

from poetry.packages import dependency_from_pep_508
from poetry.packages import ProjectPackage
from poetry.repositories.installed_repository import InstalledRepository
from poetry.repositories.pool import Pool
from poetry.repositories.repository import Repository
from poetry.puzzle import Solver
from poetry.puzzle.exceptions import SolverProblemError
from poetry.utils._compat import Path
from poetry.version.markers import parse_marker

from tests.helpers import get_dependency
from tests.helpers import get_package
from tests.repositories.test_legacy_repository import (
    MockRepository as MockLegacyRepository,
)
from tests.repositories.test_pypi_repository import MockRepository as MockPyPIRepository


@pytest.fixture()
def io():
    return OutputStyle(NullOutput())


@pytest.fixture()
def package():
    return ProjectPackage("root", "1.0")


@pytest.fixture()
def installed():
    return InstalledRepository()


@pytest.fixture()
def locked():
    return Repository()


@pytest.fixture()
def repo():
    return Repository()


@pytest.fixture()
def pool(repo):
    return Pool([repo])


@pytest.fixture()
def solver(package, pool, installed, locked, io):
    return Solver(package, pool, installed, locked, io)


def check_solver_result(ops, expected):
    for e in expected:
        if "skipped" not in e:
            e["skipped"] = False

    result = []
    for op in ops:
        if "update" == op.job_type:
            result.append(
                {
                    "job": "update",
                    "from": op.initial_package,
                    "to": op.target_package,
                    "skipped": op.skipped,
                }
            )
        else:
            job = "install"
            if op.job_type == "uninstall":
                job = "remove"

            result.append({"job": job, "package": op.package, "skipped": op.skipped})

    assert result == expected


def test_solver_install_single(solver, repo, package):
    package.add_dependency("A")

    package_a = get_package("A", "1.0")
    repo.add_package(package_a)

    ops = solver.solve([get_dependency("A")])

    check_solver_result(ops, [{"job": "install", "package": package_a}])


def test_solver_remove_if_no_longer_locked(solver, locked, installed):
    package_a = get_package("A", "1.0")
    installed.add_package(package_a)
    locked.add_package(package_a)

    ops = solver.solve()

    check_solver_result(ops, [{"job": "remove", "package": package_a}])


def test_remove_non_installed(solver, repo, locked):
    package_a = get_package("A", "1.0")
    locked.add_package(package_a)

    repo.add_package(package_a)

    request = []

    ops = solver.solve(request)

    check_solver_result(ops, [{"job": "remove", "package": package_a, "skipped": True}])


def test_install_non_existing_package_fail(solver, repo, package):
    package.add_dependency("B", "1")

    package_a = get_package("A", "1.0")
    repo.add_package(package_a)

    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_with_deps(solver, repo, package):
    package.add_dependency("A")

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    new_package_b = get_package("B", "1.1")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(new_package_b)

    package_a.requires.append(get_dependency("B", "<1.1"))

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )


def test_install_honours_not_equal(solver, repo, package):
    package.add_dependency("A")

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    new_package_b11 = get_package("B", "1.1")
    new_package_b12 = get_package("B", "1.2")
    new_package_b13 = get_package("B", "1.3")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(new_package_b11)
    repo.add_package(new_package_b12)
    repo.add_package(new_package_b13)

    package_a.requires.append(get_dependency("B", "<=1.3,!=1.3,!=1.2"))

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": new_package_b11},
            {"job": "install", "package": package_a},
        ],
    )


def test_install_with_deps_in_order(solver, repo, package):
    package.add_dependency("A")
    package.add_dependency("B")
    package.add_dependency("C")

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    package_b.requires.append(get_dependency("A", ">=1.0"))
    package_b.requires.append(get_dependency("C", ">=1.0"))

    package_c.requires.append(get_dependency("A", ">=1.0"))

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_b},
        ],
    )


def test_install_installed(solver, repo, installed, package):
    package.add_dependency("A")

    package_a = get_package("A", "1.0")
    installed.add_package(package_a)
    repo.add_package(package_a)

    ops = solver.solve()

    check_solver_result(
        ops, [{"job": "install", "package": package_a, "skipped": True}]
    )


def test_update_installed(solver, repo, installed, package):
    package.add_dependency("A")

    installed.add_package(get_package("A", "1.0"))

    package_a = get_package("A", "1.0")
    new_package_a = get_package("A", "1.1")
    repo.add_package(package_a)
    repo.add_package(new_package_a)

    ops = solver.solve()

    check_solver_result(
        ops, [{"job": "update", "from": package_a, "to": new_package_a}]
    )


def test_update_with_use_latest(solver, repo, installed, package, locked):
    package.add_dependency("A")
    package.add_dependency("B")

    installed.add_package(get_package("A", "1.0"))

    package_a = get_package("A", "1.0")
    new_package_a = get_package("A", "1.1")
    package_b = get_package("B", "1.0")
    new_package_b = get_package("B", "1.1")
    repo.add_package(package_a)
    repo.add_package(new_package_a)
    repo.add_package(package_b)
    repo.add_package(new_package_b)

    locked.add_package(package_a)
    locked.add_package(package_b)

    ops = solver.solve(use_latest=[package_b.name])

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_a, "skipped": True},
            {"job": "install", "package": new_package_b},
        ],
    )


def test_solver_sets_categories(solver, repo, package):
    package.add_dependency("A")
    package.add_dependency("B", category="dev")

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_b.add_dependency("C", "~1.0")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
        ],
    )

    assert ops[0].package.category == "dev"
    assert ops[2].package.category == "dev"
    assert ops[1].package.category == "main"


def test_solver_respects_root_package_python_versions(solver, repo, package):
    package.python_versions = "~3.4"
    package.add_dependency("A")
    package.add_dependency("B")

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_b.python_versions = "^3.3"
    package_c = get_package("C", "1.0")
    package_c.python_versions = "^3.4"
    package_c11 = get_package("C", "1.1")
    package_c11.python_versions = "^3.6"
    package_b.add_dependency("C", "^1.0")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_c11)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_fails_if_mismatch_root_python_versions(solver, repo, package):
    package.python_versions = "^3.4"
    package.add_dependency("A")
    package.add_dependency("B")

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_b.python_versions = "^3.6"
    package_c = get_package("C", "1.0")
    package_c.python_versions = "~3.3"
    package_b.add_dependency("C", "~1.0")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_solves_optional_and_compatible_packages(solver, repo, package):
    package.python_versions = "~3.4"
    package.extras["foo"] = [get_dependency("B")]
    package.add_dependency("A", {"version": "*", "python": "^3.4"})
    package.add_dependency("B", {"version": "*", "optional": True})

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_b.python_versions = "^3.3"
    package_c = get_package("C", "1.0")
    package_c.python_versions = "^3.4"
    package_b.add_dependency("C", "^1.0")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_does_not_return_extras_if_not_requested(solver, repo, package):
    package.add_dependency("A")
    package.add_dependency("B")

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")

    package_b.extras = {"foo": [get_dependency("C", "^1.0")]}

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_returns_extras_if_requested(solver, repo, package):
    package.add_dependency("A")
    package.add_dependency("B", {"version": "*", "extras": ["foo"]})

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")

    package_b.extras = {"foo": [get_dependency("C", "^1.0")]}
    package_b.add_dependency("C", {"version": "^1.0", "optional": True})

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_returns_prereleases_if_requested(solver, repo, package):
    package.add_dependency("A")
    package.add_dependency("B")
    package.add_dependency("C", {"version": "*", "allows-prereleases": True})

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_c_dev = get_package("C", "1.1-beta.1")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_c_dev)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_c_dev},
        ],
    )


def test_solver_does_not_return_prereleases_if_not_requested(solver, repo, package):
    package.add_dependency("A")
    package.add_dependency("B")
    package.add_dependency("C")

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_c_dev = get_package("C", "1.1-beta.1")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_c_dev)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_c},
        ],
    )


def test_solver_sub_dependencies_with_requirements(solver, repo, package):
    package.add_dependency("A")
    package.add_dependency("B")

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_d = get_package("D", "1.0")

    package_c.add_dependency("D", {"version": "^1.0", "python": "<4.0"})
    package_a.add_dependency("C")
    package_b.add_dependency("D", "^1.0")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_d},
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
        ],
    )

    op = ops[1]
    assert op.package.marker.is_any()


def test_solver_sub_dependencies_with_requirements_complex(solver, repo, package):
    package.add_dependency("A", {"version": "^1.0", "python": "<5.0"})
    package.add_dependency("B", {"version": "^1.0", "python": "<5.0"})
    package.add_dependency("C", {"version": "^1.0", "python": "<4.0"})

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_d = get_package("D", "1.0")
    package_e = get_package("E", "1.0")
    package_f = get_package("F", "1.0")

    package_a.add_dependency("B", {"version": "^1.0", "python": "<4.0"})
    package_a.add_dependency("D", {"version": "^1.0", "python": "<4.0"})
    package_b.add_dependency("E", {"version": "^1.0", "platform": "win32"})
    package_b.add_dependency("F", {"version": "^1.0", "python": "<5.0"})
    package_c.add_dependency("F", {"version": "^1.0", "python": "<4.0"})
    package_d.add_dependency("F")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)
    repo.add_package(package_e)
    repo.add_package(package_f)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_e},
            {"job": "install", "package": package_f},
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_d},
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_c},
        ],
    )

    op = ops[3]  # d
    assert str(op.package.marker) == 'python_version < "4.0"'

    op = ops[0]  # e
    assert str(op.package.marker) == (
        'python_version < "4.0" and sys_platform == "win32" '
        'or python_version < "5.0" and sys_platform == "win32"'
    )

    op = ops[1]  # f
    assert str(op.package.marker) == 'python_version < "5.0"'

    op = ops[4]  # a
    assert str(op.package.marker) == 'python_version < "5.0"'


def test_solver_sub_dependencies_with_not_supported_python_version(
    solver, repo, package
):
    package.python_versions = "^3.5"
    package.add_dependency("A")

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_b.python_versions = "<2.0"

    package_a.add_dependency("B", {"version": "^1.0", "python": "<2.0"})

    repo.add_package(package_a)
    repo.add_package(package_b)

    ops = solver.solve()

    check_solver_result(ops, [{"job": "install", "package": package_a}])


def test_solver_with_dependency_in_both_main_and_dev_dependencies(
    solver, repo, package
):
    package.python_versions = "^3.5"
    package.add_dependency("A")
    package.add_dependency("A", {"version": "*", "extras": ["foo"]}, category="dev")

    package_a = get_package("A", "1.0")
    package_a.extras["foo"] = [get_dependency("C")]
    package_a.add_dependency("C", {"version": "^1.0", "optional": True})
    package_a.add_dependency("B", {"version": "^1.0"})

    package_b = get_package("B", "1.0")

    package_c = get_package("C", "1.0")
    package_c.add_dependency("D", "^1.0")

    package_d = get_package("D", "1.0")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_d},
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_a},
        ],
    )

    b = ops[1].package
    c = ops[2].package
    d = ops[0].package
    a = ops[3].package

    assert d.category == "dev"
    assert c.category == "dev"
    assert b.category == "main"
    assert a.category == "main"


def test_solver_with_dependency_in_both_main_and_dev_dependencies_with_one_more_dependent(
    solver, repo, package
):
    package.add_dependency("A")
    package.add_dependency("E")
    package.add_dependency("A", {"version": "*", "extras": ["foo"]}, category="dev")

    package_a = get_package("A", "1.0")
    package_a.extras["foo"] = [get_dependency("C")]
    package_a.add_dependency("C", {"version": "^1.0", "optional": True})
    package_a.add_dependency("B", {"version": "^1.0"})

    package_b = get_package("B", "1.0")

    package_c = get_package("C", "1.0")
    package_c.add_dependency("D", "^1.0")

    package_d = get_package("D", "1.0")

    package_e = get_package("E", "1.0")
    package_e.add_dependency("A", "^1.0")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)
    repo.add_package(package_e)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_d},
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_e},
        ],
    )

    b = ops[0].package
    c = ops[3].package
    d = ops[1].package
    a = ops[2].package
    e = ops[4].package

    assert d.category == "dev"
    assert c.category == "dev"
    assert b.category == "main"
    assert a.category == "main"
    assert e.category == "main"


def test_solver_with_dependency_and_prerelease_sub_dependencies(solver, repo, package):
    package.add_dependency("A")

    package_a = get_package("A", "1.0")
    package_a.add_dependency("B", ">=1.0.0.dev2")

    repo.add_package(package_a)
    repo.add_package(get_package("B", "0.9.0"))
    repo.add_package(get_package("B", "1.0.0.dev1"))
    repo.add_package(get_package("B", "1.0.0.dev2"))
    repo.add_package(get_package("B", "1.0.0.dev3"))
    package_b = get_package("B", "1.0.0.dev4")
    repo.add_package(package_b)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )


def test_solver_circular_dependency(solver, repo, package):
    package.add_dependency("A")

    package_a = get_package("A", "1.0")
    package_a.add_dependency("B", "^1.0")

    package_b = get_package("B", "1.0")
    package_b.add_dependency("A", "^1.0")

    repo.add_package(package_a)
    repo.add_package(package_b)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )


def test_solver_duplicate_dependencies_same_constraint(solver, repo, package):
    package.add_dependency("A")

    package_a = get_package("A", "1.0")
    package_a.add_dependency("B", {"version": "^1.0", "python": "2.7"})
    package_a.add_dependency("B", {"version": "^1.0", "python": ">=3.4"})

    package_b = get_package("B", "1.0")

    repo.add_package(package_a)
    repo.add_package(package_b)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )

    op = ops[0]
    assert (
        str(op.package.marker) == 'python_version == "2.7" or python_version >= "3.4"'
    )


def test_solver_duplicate_dependencies_different_constraints(solver, repo, package):
    package.add_dependency("A")

    package_a = get_package("A", "1.0")
    package_a.add_dependency("B", {"version": "^1.0", "python": "<3.4"})
    package_a.add_dependency("B", {"version": "^2.0", "python": ">=3.4"})

    package_b10 = get_package("B", "1.0")
    package_b20 = get_package("B", "2.0")

    repo.add_package(package_a)
    repo.add_package(package_b10)
    repo.add_package(package_b20)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_b10},
            {"job": "install", "package": package_b20},
            {"job": "install", "package": package_a},
        ],
    )

    op = ops[0]
    assert str(op.package.marker) == 'python_version < "3.4"'

    op = ops[1]
    assert str(op.package.marker) == 'python_version >= "3.4"'


def test_solver_duplicate_dependencies_different_constraints_same_requirements(
    solver, repo, package
):
    package.add_dependency("A")

    package_a = get_package("A", "1.0")
    package_a.add_dependency("B", {"version": "^1.0"})
    package_a.add_dependency("B", {"version": "^2.0"})

    package_b10 = get_package("B", "1.0")
    package_b20 = get_package("B", "2.0")

    repo.add_package(package_a)
    repo.add_package(package_b10)
    repo.add_package(package_b20)

    with pytest.raises(SolverProblemError) as e:
        solver.solve()

    expected = """\
Because a (1.0) depends on both B (^1.0) and B (^2.0), a is forbidden.
So, because no versions of a match !=1.0
 and root depends on A (*), version solving failed."""

    assert str(e.value) == expected


def test_solver_duplicate_dependencies_sub_dependencies(solver, repo, package):
    package.add_dependency("A")

    package_a = get_package("A", "1.0")
    package_a.add_dependency("B", {"version": "^1.0", "python": "<3.4"})
    package_a.add_dependency("B", {"version": "^2.0", "python": ">=3.4"})

    package_b10 = get_package("B", "1.0")
    package_b20 = get_package("B", "2.0")
    package_b10.add_dependency("C", "1.2")
    package_b20.add_dependency("C", "1.5")

    package_c12 = get_package("C", "1.2")
    package_c15 = get_package("C", "1.5")

    repo.add_package(package_a)
    repo.add_package(package_b10)
    repo.add_package(package_b20)
    repo.add_package(package_c12)
    repo.add_package(package_c15)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_c12},
            {"job": "install", "package": package_c15},
            {"job": "install", "package": package_b10},
            {"job": "install", "package": package_b20},
            {"job": "install", "package": package_a},
        ],
    )

    op = ops[2]
    assert str(op.package.marker) == 'python_version < "3.4"'

    op = ops[3]
    assert str(op.package.marker) == 'python_version >= "3.4"'


def test_solver_fails_if_dependency_name_does_not_match_package(solver, repo, package):
    package.add_dependency("my-demo", {"git": "https://github.com/demo/demo.git"})

    with pytest.raises(RuntimeError):
        solver.solve()


def test_solver_does_not_get_stuck_in_recursion_on_circular_dependency(
    solver, repo, package
):
    package_a = get_package("A", "1.0")
    package_a.add_dependency("B", "^1.0")
    package_b = get_package("B", "1.0")
    package_b.add_dependency("C", "^1.0")
    package_c = get_package("C", "1.0")
    package_c.add_dependency("B", "^1.0")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    package.add_dependency("A", "^1.0")

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )


def test_solver_can_resolve_git_dependencies(solver, repo, package):
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    package.add_dependency("demo", {"git": "https://github.com/demo/demo.git"})

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": pendulum},
            {"job": "install", "package": get_package("demo", "0.1.2")},
        ],
    )


def test_solver_can_resolve_git_dependencies_with_extras(solver, repo, package):
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    package.add_dependency(
        "demo", {"git": "https://github.com/demo/demo.git", "extras": ["foo"]}
    )

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": cleo},
            {"job": "install", "package": pendulum},
            {"job": "install", "package": get_package("demo", "0.1.2")},
        ],
    )


def test_solver_does_not_trigger_conflict_for_python_constraint_if_python_requirement_is_compatible(
    solver, repo, package
):
    package.python_versions = "~2.7 || ^3.4"
    package.add_dependency("A", {"version": "^1.0", "python": "^3.6"})

    package_a = get_package("A", "1.0.0")
    package_a.python_versions = ">=3.6"

    repo.add_package(package_a)

    ops = solver.solve()

    check_solver_result(ops, [{"job": "install", "package": package_a}])

    assert (
        str(ops[0].package.marker)
        == 'python_version >= "3.6" and python_version < "4.0"'
    )


def test_solver_does_not_trigger_conflict_for_python_constraint_if_python_requirement_is_compatible_multiple(
    solver, repo, package
):
    package.python_versions = "~2.7 || ^3.4"
    package.add_dependency("A", {"version": "^1.0", "python": "^3.6"})
    package.add_dependency("B", {"version": "^1.0", "python": "^3.5.3"})

    package_a = get_package("A", "1.0.0")
    package_a.python_versions = ">=3.6"
    package_a.add_dependency("B", "^1.0")

    package_b = get_package("B", "1.0.0")
    package_b.python_versions = ">=3.5.3"

    repo.add_package(package_a)
    repo.add_package(package_b)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )

    assert str(ops[0].package.marker) == (
        'python_version >= "3.6" and python_version < "4.0" '
        'or python_version >= "3.5.3" and python_version < "4.0.0"'
    )


def test_solver_triggers_conflict_for_dependency_python_not_fully_compatible_with_package_python(
    solver, repo, package
):
    package.python_versions = "~2.7 || ^3.4"
    package.add_dependency("A", {"version": "^1.0", "python": "^3.5"})

    package_a = get_package("A", "1.0.0")
    package_a.python_versions = ">=3.6"

    repo.add_package(package_a)

    with pytest.raises(SolverProblemError):
        solver.solve()


@pytest.mark.skip(
    "This is not working at the moment due to limitations in the resolver"
)
def test_solver_finds_compatible_package_for_dependency_python_not_fully_compatible_with_package_python(
    solver, repo, package
):
    package.python_versions = "~2.7 || ^3.4"
    package.add_dependency("A", {"version": "^1.0", "python": "^3.5"})

    package_a101 = get_package("A", "1.0.1")
    package_a101.python_versions = ">=3.6"

    package_a100 = get_package("A", "1.0.0")
    package_a100.python_versions = ">=3.5"

    repo.add_package(package_a100)
    repo.add_package(package_a101)

    ops = solver.solve()

    check_solver_result(ops, [{"job": "install", "package": package_a100}])

    assert (
        str(ops[0].package.marker)
        == 'python_version >= "3.5" and python_version < "4.0"'
    )


def test_solver_sets_appropriate_markers_when_solving(solver, repo, package):
    dep = dependency_from_pep_508(
        'B (>=1.0); python_version >= "3.6" and sys_platform != "win32"'
    )

    package.add_dependency("A", "^1.0")

    package_a = get_package("A", "1.0.0")
    package_a.requires.append(dep)

    package_b = get_package("B", "1.0.0")

    repo.add_package(package_a)
    repo.add_package(package_b)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )

    assert (
        str(ops[0].package.marker)
        == 'python_version >= "3.6" and sys_platform != "win32"'
    )

    assert str(ops[1].package.marker) == ""


def test_solver_does_not_trigger_new_resolution_on_duplicate_dependencies_if_only_extras(
    solver, repo, package
):
    dep1 = dependency_from_pep_508('B (>=1.0); extra == "foo"')
    dep1.activate()
    dep2 = dependency_from_pep_508('B (>=2.0); extra == "bar"')
    dep2.activate()

    package.add_dependency("A", {"version": "^1.0", "extras": ["foo", "bar"]})

    package_a = get_package("A", "1.0.0")
    package_a.extras = {"foo": [dep1], "bar": [dep2]}
    package_a.requires.append(dep1)
    package_a.requires.append(dep2)

    package_b2 = get_package("B", "2.0.0")
    package_b1 = get_package("B", "1.0.0")

    repo.add_package(package_a)
    repo.add_package(package_b1)
    repo.add_package(package_b2)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_b2},
            {"job": "install", "package": package_a},
        ],
    )

    assert str(ops[0].package.marker) in [
        'extra == "foo" or extra == "bar"',
        'extra == "bar" or extra == "foo"',
    ]
    assert str(ops[1].package.marker) == ""


def test_solver_does_not_raise_conflict_for_locked_conditional_dependencies(
    solver, repo, package
):
    package.python_versions = "~2.7 || ^3.4"
    package.add_dependency("A", {"version": "^1.0", "python": "^3.6"})
    package.add_dependency("B", "^1.0")

    package_a = get_package("A", "1.0.0")
    package_a.python_versions = ">=3.6"
    package_a.marker = parse_marker(
        'python_version >= "3.6" and python_version < "4.0"'
    )

    package_b = get_package("B", "1.0.0")

    repo.add_package(package_a)
    repo.add_package(package_b)

    solver._locked = Repository([package_a])
    ops = solver.solve(use_latest=[package_b.name])

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_returns_extras_if_requested_in_dependencies_and_not_in_root_package(
    solver, repo, package
):
    package.add_dependency("A")
    package.add_dependency("B")
    package.add_dependency("C")

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_d = get_package("D", "1.0")

    package_b.add_dependency("C", {"version": "^1.0", "extras": ["foo"]})

    package_c.add_dependency("D", {"version": "^1.0", "optional": True})
    package_c.extras = {"foo": [get_dependency("D", "^1.0")]}

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_d},
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_should_not_resolve_prerelease_version_if_not_requested(
    solver, repo, package
):
    package.add_dependency("A", "~1.8.0")
    package.add_dependency("B", "^0.5.0")

    package_a185 = get_package("A", "1.8.5")
    package_a19b1 = get_package("A", "1.9b1")
    package_b = get_package("B", "0.5.0")
    package_b.add_dependency("A", ">=1.9b1")

    repo.add_package(package_a185)
    repo.add_package(package_a19b1)
    repo.add_package(package_b)

    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_ignores_dependencies_with_incompatible_python_full_version_marker(
    solver, repo, package
):
    package.python_versions = "^3.6"
    package.add_dependency("A", "^1.0")
    package.add_dependency("B", "^2.0")

    package_a = get_package("A", "1.0.0")
    package_a.requires.append(
        dependency_from_pep_508(
            'B (<2.0); platform_python_implementation == "PyPy" and python_full_version < "2.7.9"'
        )
    )

    package_b200 = get_package("B", "2.0.0")
    package_b100 = get_package("B", "1.0.0")

    repo.add_package(package_a)
    repo.add_package(package_b100)
    repo.add_package(package_b200)

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b200},
        ],
    )


def test_solver_git_dependencies_update(solver, repo, package, installed):
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    demo = get_package("demo", "0.1.2")
    demo.source_type = "git"
    demo.source_url = "https://github.com/demo/demo.git"
    demo.source_reference = "123456"
    installed.add_package(demo)

    package.add_dependency("demo", {"git": "https://github.com/demo/demo.git"})

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": pendulum},
            {
                "job": "update",
                "from": get_package("demo", "0.1.2"),
                "to": get_package("demo", "0.1.2"),
            },
        ],
    )

    op = ops[1]

    assert op.job_type == "update"
    assert op.package.source_type == "git"
    assert op.package.source_reference.startswith("9cf87a2")
    assert op.initial_package.source_reference == "123456"


def test_solver_git_dependencies_update_skipped(solver, repo, package, installed):
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    demo = get_package("demo", "0.1.2")
    demo.source_type = "git"
    demo.source_url = "https://github.com/demo/demo.git"
    demo.source_reference = "9cf87a285a2d3fbb0b9fa621997b3acc3631ed24"
    installed.add_package(demo)

    package.add_dependency("demo", {"git": "https://github.com/demo/demo.git"})

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": pendulum},
            {
                "job": "install",
                "package": get_package("demo", "0.1.2"),
                "skipped": True,
            },
        ],
    )


def test_solver_can_resolve_directory_dependencies(solver, repo, package):
    pendulum = get_package("pendulum", "2.0.3")
    repo.add_package(pendulum)

    path = (
        Path(__file__).parent.parent
        / "fixtures"
        / "git"
        / "github.com"
        / "demo"
        / "demo"
    ).as_posix()

    package.add_dependency("demo", {"path": path})

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": pendulum},
            {"job": "install", "package": get_package("demo", "0.1.2")},
        ],
    )

    op = ops[1]

    assert op.package.name == "demo"
    assert op.package.version.text == "0.1.2"
    assert op.package.source_type == "directory"
    assert op.package.source_url == path


def test_solver_can_resolve_directory_dependencies_with_extras(solver, repo, package):
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    path = (
        Path(__file__).parent.parent
        / "fixtures"
        / "git"
        / "github.com"
        / "demo"
        / "demo"
    ).as_posix()

    package.add_dependency("demo", {"path": path, "extras": ["foo"]})

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": cleo},
            {"job": "install", "package": pendulum},
            {"job": "install", "package": get_package("demo", "0.1.2")},
        ],
    )

    op = ops[2]

    assert op.package.name == "demo"
    assert op.package.version.text == "0.1.2"
    assert op.package.source_type == "directory"
    assert op.package.source_url == path


def test_solver_can_resolve_sdist_dependencies(solver, repo, package):
    pendulum = get_package("pendulum", "2.0.3")
    repo.add_package(pendulum)

    path = (
        Path(__file__).parent.parent
        / "fixtures"
        / "distributions"
        / "demo-0.1.0.tar.gz"
    ).as_posix()

    package.add_dependency("demo", {"path": path})

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": pendulum},
            {"job": "install", "package": get_package("demo", "0.1.0")},
        ],
    )

    op = ops[1]

    assert op.package.name == "demo"
    assert op.package.version.text == "0.1.0"
    assert op.package.source_type == "file"
    assert op.package.source_url == path


def test_solver_can_resolve_sdist_dependencies_with_extras(solver, repo, package):
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    path = (
        Path(__file__).parent.parent
        / "fixtures"
        / "distributions"
        / "demo-0.1.0.tar.gz"
    ).as_posix()

    package.add_dependency("demo", {"path": path, "extras": ["foo"]})

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": cleo},
            {"job": "install", "package": pendulum},
            {"job": "install", "package": get_package("demo", "0.1.0")},
        ],
    )

    op = ops[2]

    assert op.package.name == "demo"
    assert op.package.version.text == "0.1.0"
    assert op.package.source_type == "file"
    assert op.package.source_url == path


def test_solver_can_resolve_wheel_dependencies(solver, repo, package):
    pendulum = get_package("pendulum", "2.0.3")
    repo.add_package(pendulum)

    path = (
        Path(__file__).parent.parent
        / "fixtures"
        / "distributions"
        / "demo-0.1.0-py2.py3-none-any.whl"
    ).as_posix()

    package.add_dependency("demo", {"path": path})

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": pendulum},
            {"job": "install", "package": get_package("demo", "0.1.0")},
        ],
    )

    op = ops[1]

    assert op.package.name == "demo"
    assert op.package.version.text == "0.1.0"
    assert op.package.source_type == "file"
    assert op.package.source_url == path


def test_solver_can_resolve_wheel_dependencies_with_extras(solver, repo, package):
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    path = (
        Path(__file__).parent.parent
        / "fixtures"
        / "distributions"
        / "demo-0.1.0-py2.py3-none-any.whl"
    ).as_posix()

    package.add_dependency("demo", {"path": path, "extras": ["foo"]})

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": cleo},
            {"job": "install", "package": pendulum},
            {"job": "install", "package": get_package("demo", "0.1.0")},
        ],
    )

    op = ops[2]

    assert op.package.name == "demo"
    assert op.package.version.text == "0.1.0"
    assert op.package.source_type == "file"
    assert op.package.source_url == path


def test_solver_can_solve_with_legacy_repository_using_proper_dists(
    package, installed, locked, io
):
    repo = MockLegacyRepository()
    pool = Pool([repo])

    solver = Solver(package, pool, installed, locked, io)

    package.add_dependency("isort", "4.3.4")

    ops = solver.solve()

    check_solver_result(
        ops,
        [
            {"job": "install", "package": get_package("futures", "3.2.0")},
            {"job": "install", "package": get_package("isort", "4.3.4")},
        ],
    )

    futures = ops[0].package
    assert futures.python_versions == ">=2.6, <3"


def test_solver_can_solve_with_legacy_repository_using_proper_python_compatible_dists(
    package, installed, locked, io
):
    package.python_versions = "^3.7"

    repo = MockLegacyRepository()
    pool = Pool([repo])

    solver = Solver(package, pool, installed, locked, io)

    package.add_dependency("isort", "4.3.4")

    ops = solver.solve()

    check_solver_result(
        ops, [{"job": "install", "package": get_package("isort", "4.3.4")}]
    )


def test_solver_skips_invalid_versions(package, installed, locked, io):
    package.python_versions = "^3.7"

    repo = MockPyPIRepository()
    pool = Pool([repo])

    solver = Solver(package, pool, installed, locked, io)

    package.add_dependency("trackpy", "^0.4")

    ops = solver.solve()

    check_solver_result(
        ops, [{"job": "install", "package": get_package("trackpy", "0.4.1")}]
    )


def test_multiple_constraints_on_root(package, solver, repo):
    package.add_dependency("foo", {"version": "^1.0", "python": "^2.7"})
    package.add_dependency("foo", {"version": "^2.0", "python": "^3.7"})

    foo15 = get_package("foo", "1.5.0")
    foo25 = get_package("foo", "2.5.0")

    repo.add_package(foo15)
    repo.add_package(foo25)

    ops = solver.solve()

    check_solver_result(
        ops,
        [{"job": "install", "package": foo15}, {"job": "install", "package": foo25}],
    )
