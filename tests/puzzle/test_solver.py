from pathlib import Path

import pytest

from cleo.io.null_io import NullIO

from poetry.core.packages.dependency import Dependency
from poetry.core.packages.package import Package
from poetry.core.packages.project_package import ProjectPackage
from poetry.core.version.markers import parse_marker
from poetry.factory import Factory
from poetry.puzzle import Solver
from poetry.puzzle.exceptions import SolverProblemError
from poetry.puzzle.provider import Provider as BaseProvider
from poetry.repositories.installed_repository import InstalledRepository
from poetry.repositories.pool import Pool
from poetry.repositories.repository import Repository
from poetry.utils.env import MockEnv
from tests.helpers import get_dependency
from tests.helpers import get_package
from tests.repositories.test_legacy_repository import (
    MockRepository as MockLegacyRepository,
)
from tests.repositories.test_pypi_repository import MockRepository as MockPyPIRepository


class Provider(BaseProvider):
    def set_package_python_versions(self, python_versions):
        self._package.python_versions = python_versions
        self._python_constraint = self._package.python_constraint


@pytest.fixture()
def io():
    return NullIO()


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
    return Solver(
        package, pool, installed, locked, io, provider=Provider(package, pool, io)
    )


def check_solver_result(transaction, expected, synchronize=False):
    for e in expected:
        if "skipped" not in e:
            e["skipped"] = False

    result = []
    ops = transaction.calculate_operations(synchronize=synchronize)
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

    assert expected == result

    return ops


def test_solver_install_single(solver, repo, package):
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    repo.add_package(package_a)

    transaction = solver.solve([get_dependency("A")])

    check_solver_result(transaction, [{"job": "install", "package": package_a}])


def test_solver_remove_if_no_longer_locked(solver, locked, installed):
    package_a = get_package("A", "1.0")
    installed.add_package(package_a)
    locked.add_package(package_a)

    transaction = solver.solve()

    check_solver_result(transaction, [{"job": "remove", "package": package_a}])


def test_remove_non_installed(solver, repo, locked):
    package_a = get_package("A", "1.0")
    locked.add_package(package_a)

    repo.add_package(package_a)

    request = []

    transaction = solver.solve(request)

    check_solver_result(transaction, [])


def test_install_non_existing_package_fail(solver, repo, package):
    package.add_dependency(Factory.create_dependency("B", "1"))

    package_a = get_package("A", "1.0")
    repo.add_package(package_a)

    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_with_deps(solver, repo, package):
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    new_package_b = get_package("B", "1.1")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(new_package_b)

    package_a.add_dependency(get_dependency("B", "<1.1"))

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )


def test_install_honours_not_equal(solver, repo, package):
    package.add_dependency(Factory.create_dependency("A", "*"))

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

    package_a.add_dependency(get_dependency("B", "<=1.3,!=1.3,!=1.2"))

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": new_package_b11},
            {"job": "install", "package": package_a},
        ],
    )


def test_install_with_deps_in_order(solver, repo, package):
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("B", "*"))
    package.add_dependency(Factory.create_dependency("C", "*"))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    package_b.add_dependency(get_dependency("A", ">=1.0"))
    package_b.add_dependency(get_dependency("C", ">=1.0"))

    package_c.add_dependency(get_dependency("A", ">=1.0"))

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_b},
        ],
    )


def test_install_installed(solver, repo, installed, package):
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    installed.add_package(package_a)
    repo.add_package(package_a)

    transaction = solver.solve()

    check_solver_result(
        transaction, [{"job": "install", "package": package_a, "skipped": True}]
    )


def test_update_installed(solver, repo, installed, package):
    package.add_dependency(Factory.create_dependency("A", "*"))

    installed.add_package(get_package("A", "1.0"))

    package_a = get_package("A", "1.0")
    new_package_a = get_package("A", "1.1")
    repo.add_package(package_a)
    repo.add_package(new_package_a)

    transaction = solver.solve()

    check_solver_result(
        transaction, [{"job": "update", "from": package_a, "to": new_package_a}]
    )


def test_update_with_use_latest(solver, repo, installed, package, locked):
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("B", "*"))

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

    transaction = solver.solve(use_latest=[package_b.name])

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_a, "skipped": True},
            {"job": "install", "package": new_package_b},
        ],
    )


def test_solver_sets_groups(solver, repo, package):
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("B", "*", groups=["dev"]))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_b.add_dependency(Factory.create_dependency("C", "~1.0"))

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
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
    solver.provider.set_package_python_versions("~3.4")
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("B", "*"))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_b.python_versions = "^3.3"
    package_c = get_package("C", "1.0")
    package_c.python_versions = "^3.4"
    package_c11 = get_package("C", "1.1")
    package_c11.python_versions = "^3.6"
    package_b.add_dependency(Factory.create_dependency("C", "^1.0"))

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_c11)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_fails_if_mismatch_root_python_versions(solver, repo, package):
    solver.provider.set_package_python_versions("^3.4")
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("B", "*"))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_b.python_versions = "^3.6"
    package_c = get_package("C", "1.0")
    package_c.python_versions = "~3.3"
    package_b.add_dependency(Factory.create_dependency("C", "~1.0"))

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_solves_optional_and_compatible_packages(solver, repo, package):
    solver.provider.set_package_python_versions("~3.4")
    package.extras["foo"] = [get_dependency("B")]
    package.add_dependency(
        Factory.create_dependency("A", {"version": "*", "python": "^3.4"})
    )
    package.add_dependency(
        Factory.create_dependency("B", {"version": "*", "optional": True})
    )

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_b.python_versions = "^3.3"
    package_c = get_package("C", "1.0")
    package_c.python_versions = "^3.4"
    package_b.add_dependency(Factory.create_dependency("C", "^1.0"))

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_does_not_return_extras_if_not_requested(solver, repo, package):
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("B", "*"))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")

    package_b.extras = {"foo": [get_dependency("C", "^1.0")]}

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_returns_extras_if_requested(solver, repo, package):
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(
        Factory.create_dependency("B", {"version": "*", "extras": ["foo"]})
    )

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")

    dep = get_dependency("C", "^1.0", optional=True)
    dep.marker = parse_marker("extra == 'foo'")
    package_b.extras = {"foo": [dep]}
    package_b.add_dependency(dep)

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
        ],
    )

    assert ops[-1].package.marker.is_any()
    assert ops[0].package.marker.is_any()


@pytest.mark.parametrize(("enabled_extra",), [("one",), ("two",), (None,)])
def test_solver_returns_extras_only_requested(solver, repo, package, enabled_extra):
    extras = [enabled_extra] if enabled_extra is not None else []

    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(
        Factory.create_dependency("B", {"version": "*", "extras": extras})
    )

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c10 = get_package("C", "1.0")
    package_c20 = get_package("C", "2.0")

    dep10 = get_dependency("C", "1.0", optional=True)
    dep10._in_extras.append("one")
    dep10.marker = parse_marker("extra == 'one'")

    dep20 = get_dependency("C", "2.0", optional=True)
    dep20._in_extras.append("two")
    dep20.marker = parse_marker("extra == 'two'")

    package_b.extras = {"one": [dep10], "two": [dep20]}

    package_b.add_dependency(dep10)
    package_b.add_dependency(dep20)

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c10)
    repo.add_package(package_c20)

    transaction = solver.solve()

    expected = [
        {"job": "install", "package": package_a},
        {"job": "install", "package": package_b},
    ]

    if enabled_extra is not None:
        expected.insert(
            0,
            {
                "job": "install",
                "package": package_c10 if enabled_extra == "one" else package_c20,
            },
        )

    ops = check_solver_result(
        transaction,
        expected,
    )

    assert ops[-1].package.marker.is_any()
    assert ops[0].package.marker.is_any()


@pytest.mark.parametrize(("enabled_extra",), [("one",), ("two",), (None,)])
def test_solver_returns_extras_when_multiple_extras_use_same_dependency(
    solver, repo, package, enabled_extra
):
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")

    dep = get_dependency("C", "*", optional=True)
    dep._in_extras.append("one")
    dep._in_extras.append("two")

    package_b.extras = {"one": [dep], "two": [dep]}

    package_b.add_dependency(dep)

    extras = [enabled_extra] if enabled_extra is not None else []
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "*", "extras": extras})
    )

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    transaction = solver.solve()

    expected = [
        {"job": "install", "package": package_b},
        {"job": "install", "package": package_a},
    ]

    if enabled_extra is not None:
        expected.insert(0, {"job": "install", "package": package_c})

    ops = check_solver_result(
        transaction,
        expected,
    )

    assert ops[-1].package.marker.is_any()
    assert ops[0].package.marker.is_any()


@pytest.mark.parametrize(("enabled_extra",), [("one",), ("two",), (None,)])
def test_solver_returns_extras_only_requested_nested(
    solver, repo, package, enabled_extra
):
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c10 = get_package("C", "1.0")
    package_c20 = get_package("C", "2.0")

    dep10 = get_dependency("C", "1.0", optional=True)
    dep10._in_extras.append("one")
    dep10.marker = parse_marker("extra == 'one'")

    dep20 = get_dependency("C", "2.0", optional=True)
    dep20._in_extras.append("two")
    dep20.marker = parse_marker("extra == 'two'")

    package_b.extras = {"one": [dep10], "two": [dep20]}

    package_b.add_dependency(dep10)
    package_b.add_dependency(dep20)

    extras = [enabled_extra] if enabled_extra is not None else []
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "*", "extras": extras})
    )

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c10)
    repo.add_package(package_c20)

    transaction = solver.solve()

    expected = [
        {"job": "install", "package": package_b},
        {"job": "install", "package": package_a},
    ]

    if enabled_extra is not None:
        expected.insert(
            0,
            {
                "job": "install",
                "package": package_c10 if enabled_extra == "one" else package_c20,
            },
        )

    ops = check_solver_result(transaction, expected)

    assert ops[-1].package.marker.is_any()
    assert ops[0].package.marker.is_any()


def test_solver_returns_prereleases_if_requested(solver, repo, package):
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("B", "*"))
    package.add_dependency(
        Factory.create_dependency("C", {"version": "*", "allow-prereleases": True})
    )

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_c_dev = get_package("C", "1.1-beta.1")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_c_dev)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_c_dev},
        ],
    )


def test_solver_does_not_return_prereleases_if_not_requested(solver, repo, package):
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("B", "*"))
    package.add_dependency(Factory.create_dependency("C", "*"))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_c_dev = get_package("C", "1.1-beta.1")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_c_dev)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_c},
        ],
    )


def test_solver_sub_dependencies_with_requirements(solver, repo, package):
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("B", "*"))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_d = get_package("D", "1.0")

    package_c.add_dependency(
        Factory.create_dependency("D", {"version": "^1.0", "python": "<4.0"})
    )
    package_a.add_dependency(Factory.create_dependency("C", "*"))
    package_b.add_dependency(Factory.create_dependency("D", "^1.0"))

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
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
    package.add_dependency(
        Factory.create_dependency("A", {"version": "^1.0", "python": "<5.0"})
    )
    package.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "python": "<5.0"})
    )
    package.add_dependency(
        Factory.create_dependency("C", {"version": "^1.0", "python": "<4.0"})
    )

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_d = get_package("D", "1.0")
    package_e = get_package("E", "1.0")
    package_f = get_package("F", "1.0")

    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "python": "<4.0"})
    )
    package_a.add_dependency(
        Factory.create_dependency("D", {"version": "^1.0", "python": "<4.0"})
    )
    package_b.add_dependency(
        Factory.create_dependency("E", {"version": "^1.0", "platform": "win32"})
    )
    package_b.add_dependency(
        Factory.create_dependency("F", {"version": "^1.0", "python": "<5.0"})
    )
    package_c.add_dependency(
        Factory.create_dependency("F", {"version": "^1.0", "python": "<4.0"})
    )
    package_d.add_dependency(Factory.create_dependency("F", "*"))

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)
    repo.add_package(package_e)
    repo.add_package(package_f)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_e},
            {"job": "install", "package": package_f},
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_d},
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_c},
        ],
    )


def test_solver_sub_dependencies_with_not_supported_python_version(
    solver, repo, package
):
    solver.provider.set_package_python_versions("^3.5")
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_b.python_versions = "<2.0"

    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "python": "<2.0"})
    )

    repo.add_package(package_a)
    repo.add_package(package_b)

    transaction = solver.solve()

    check_solver_result(transaction, [{"job": "install", "package": package_a}])


def test_solver_sub_dependencies_with_not_supported_python_version_transitive(
    solver, repo, package
):
    solver.provider.set_package_python_versions("^3.4")

    package.add_dependency(
        Factory.create_dependency("httpx", {"version": "^0.17.1", "python": "^3.6"})
    )

    httpx = get_package("httpx", "0.17.1")
    httpx.python_versions = ">=3.6"

    httpcore = get_package("httpcore", "0.12.3")
    httpcore.python_versions = ">=3.6"

    sniffio_1_1_0 = get_package("sniffio", "1.1.0")
    sniffio_1_1_0.python_versions = ">=3.5"

    sniffio = get_package("sniffio", "1.2.0")
    sniffio.python_versions = ">=3.5"

    httpx.add_dependency(
        Factory.create_dependency("httpcore", {"version": ">=0.12.1,<0.13"})
    )
    httpx.add_dependency(Factory.create_dependency("sniffio", {"version": "*"}))
    httpcore.add_dependency(Factory.create_dependency("sniffio", {"version": "==1.*"}))

    repo.add_package(httpx)
    repo.add_package(httpcore)
    repo.add_package(sniffio)
    repo.add_package(sniffio_1_1_0)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": sniffio, "skipped": False},
            {"job": "install", "package": httpcore, "skipped": False},
            {"job": "install", "package": httpx, "skipped": False},
        ],
    )


def test_solver_with_dependency_in_both_default_and_dev_dependencies(
    solver, repo, package
):
    solver.provider.set_package_python_versions("^3.5")
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(
        Factory.create_dependency(
            "A", {"version": "*", "extras": ["foo"]}, groups=["dev"]
        )
    )

    package_a = get_package("A", "1.0")
    package_a.extras["foo"] = [get_dependency("C")]
    package_a.add_dependency(
        Factory.create_dependency("C", {"version": "^1.0", "optional": True})
    )
    package_a.add_dependency(Factory.create_dependency("B", {"version": "^1.0"}))

    package_b = get_package("B", "1.0")

    package_c = get_package("C", "1.0")
    package_c.add_dependency(Factory.create_dependency("D", "^1.0"))

    package_d = get_package("D", "1.0")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_d},
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_a},
        ],
    )

    d = ops[0].package
    b = ops[1].package
    c = ops[2].package
    a = ops[3].package

    assert d.category == "dev"
    assert b.category == "main"
    assert c.category == "dev"
    assert a.category == "main"


def test_solver_with_dependency_in_both_main_and_dev_dependencies_with_one_more_dependent(
    solver, repo, package
):
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("E", "*"))
    package.add_dependency(
        Factory.create_dependency(
            "A", {"version": "*", "extras": ["foo"]}, groups=["dev"]
        )
    )

    package_a = get_package("A", "1.0")
    package_a.extras["foo"] = [get_dependency("C")]
    package_a.add_dependency(
        Factory.create_dependency("C", {"version": "^1.0", "optional": True})
    )
    package_a.add_dependency(Factory.create_dependency("B", {"version": "^1.0"}))

    package_b = get_package("B", "1.0")

    package_c = get_package("C", "1.0")
    package_c.add_dependency(Factory.create_dependency("D", "^1.0"))

    package_d = get_package("D", "1.0")

    package_e = get_package("E", "1.0")
    package_e.add_dependency(Factory.create_dependency("A", "^1.0"))

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)
    repo.add_package(package_e)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_d},
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_e},
        ],
    )

    b = ops[0].package
    d = ops[1].package
    a = ops[2].package
    c = ops[3].package
    e = ops[4].package

    assert b.category == "main"
    assert d.category == "dev"
    assert a.category == "main"
    assert c.category == "dev"
    assert e.category == "main"


def test_solver_with_dependency_and_prerelease_sub_dependencies(solver, repo, package):
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_a.add_dependency(Factory.create_dependency("B", ">=1.0.0.dev2"))

    repo.add_package(package_a)
    repo.add_package(get_package("B", "0.9.0"))
    repo.add_package(get_package("B", "1.0.0.dev1"))
    repo.add_package(get_package("B", "1.0.0.dev2"))
    repo.add_package(get_package("B", "1.0.0.dev3"))
    package_b = get_package("B", "1.0.0.dev4")
    repo.add_package(package_b)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )


def test_solver_circular_dependency(solver, repo, package):
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_a.add_dependency(Factory.create_dependency("B", "^1.0"))

    package_b = get_package("B", "1.0")
    package_b.add_dependency(Factory.create_dependency("A", "^1.0"))
    package_b.add_dependency(Factory.create_dependency("C", "^1.0"))

    package_c = get_package("C", "1.0")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )

    assert "main" == ops[0].package.category


def test_solver_circular_dependency_chain(solver, repo, package):
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_a.add_dependency(Factory.create_dependency("B", "^1.0"))

    package_b = get_package("B", "1.0")
    package_b.add_dependency(Factory.create_dependency("C", "^1.0"))

    package_c = get_package("C", "1.0")
    package_c.add_dependency(Factory.create_dependency("D", "^1.0"))

    package_d = get_package("D", "1.0")
    package_d.add_dependency(Factory.create_dependency("B", "^1.0"))

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_d},
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )

    assert "main" == ops[0].package.category


def test_solver_dense_dependencies(solver, repo, package):
    # The root package depends on packages A0...An-1,
    # And package Ai depends  on packages A0...Ai-1
    # This graph is a transitive tournament
    packages = []
    n = 22
    for i in range(n):
        package_ai = get_package("a" + str(i), "1.0")
        repo.add_package(package_ai)
        packages.append(package_ai)
        package.add_dependency(Factory.create_dependency("a" + str(i), "^1.0"))
        for j in range(i):
            package_ai.add_dependency(Factory.create_dependency("a" + str(j), "^1.0"))

    transaction = solver.solve()

    check_solver_result(
        transaction, [{"job": "install", "package": packages[i]} for i in range(n)]
    )


def test_solver_duplicate_dependencies_same_constraint(solver, repo, package):
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "python": "2.7"})
    )
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "python": ">=3.4"})
    )

    package_b = get_package("B", "1.0")

    repo.add_package(package_a)
    repo.add_package(package_b)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )


def test_solver_duplicate_dependencies_different_constraints(solver, repo, package):
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "python": "<3.4"})
    )
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^2.0", "python": ">=3.4"})
    )

    package_b10 = get_package("B", "1.0")
    package_b20 = get_package("B", "2.0")

    repo.add_package(package_a)
    repo.add_package(package_b10)
    repo.add_package(package_b20)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_b10},
            {"job": "install", "package": package_b20},
            {"job": "install", "package": package_a},
        ],
    )


def test_solver_duplicate_dependencies_different_constraints_same_requirements(
    solver, repo, package
):
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_a.add_dependency(Factory.create_dependency("B", {"version": "^1.0"}))
    package_a.add_dependency(Factory.create_dependency("B", {"version": "^2.0"}))

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
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "python": "<3.4"})
    )
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^2.0", "python": ">=3.4"})
    )

    package_b10 = get_package("B", "1.0")
    package_b20 = get_package("B", "2.0")
    package_b10.add_dependency(Factory.create_dependency("C", "1.2"))
    package_b20.add_dependency(Factory.create_dependency("C", "1.5"))

    package_c12 = get_package("C", "1.2")
    package_c15 = get_package("C", "1.5")

    repo.add_package(package_a)
    repo.add_package(package_b10)
    repo.add_package(package_b20)
    repo.add_package(package_c12)
    repo.add_package(package_c15)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_c12},
            {"job": "install", "package": package_c15},
            {"job": "install", "package": package_b10},
            {"job": "install", "package": package_b20},
            {"job": "install", "package": package_a},
        ],
    )


def test_solver_fails_if_dependency_name_does_not_match_package(solver, repo, package):
    package.add_dependency(
        Factory.create_dependency(
            "my-demo", {"git": "https://github.com/demo/demo.git"}
        )
    )

    with pytest.raises(RuntimeError):
        solver.solve()


def test_solver_does_not_get_stuck_in_recursion_on_circular_dependency(
    solver, repo, package
):
    package_a = get_package("A", "1.0")
    package_a.add_dependency(Factory.create_dependency("B", "^1.0"))
    package_b = get_package("B", "1.0")
    package_b.add_dependency(Factory.create_dependency("C", "^1.0"))
    package_c = get_package("C", "1.0")
    package_c.add_dependency(Factory.create_dependency("B", "^1.0"))

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    package.add_dependency(Factory.create_dependency("A", "^1.0"))

    transaction = solver.solve()

    check_solver_result(
        transaction,
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

    package.add_dependency(
        Factory.create_dependency("demo", {"git": "https://github.com/demo/demo.git"})
    )

    transaction = solver.solve()

    demo = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference="master",
        source_resolved_reference="9cf87a285a2d3fbb0b9fa621997b3acc3631ed24",
    )

    ops = check_solver_result(
        transaction,
        [{"job": "install", "package": pendulum}, {"job": "install", "package": demo}],
    )

    op = ops[1]

    assert op.package.source_type == "git"
    assert op.package.source_reference == "master"
    assert op.package.source_resolved_reference.startswith("9cf87a2")


def test_solver_can_resolve_git_dependencies_with_extras(solver, repo, package):
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    package.add_dependency(
        Factory.create_dependency(
            "demo", {"git": "https://github.com/demo/demo.git", "extras": ["foo"]}
        )
    )

    transaction = solver.solve()

    demo = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference="master",
        source_resolved_reference="9cf87a285a2d3fbb0b9fa621997b3acc3631ed24",
    )

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": cleo},
            {"job": "install", "package": pendulum},
            {"job": "install", "package": demo},
        ],
    )


@pytest.mark.parametrize(
    "ref",
    [{"branch": "a-branch"}, {"tag": "a-tag"}, {"rev": "9cf8"}],
    ids=["branch", "tag", "rev"],
)
def test_solver_can_resolve_git_dependencies_with_ref(solver, repo, package, ref):
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    demo = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference=ref[list(ref.keys())[0]],
        source_resolved_reference="9cf87a285a2d3fbb0b9fa621997b3acc3631ed24",
    )

    git_config = {demo.source_type: demo.source_url}
    git_config.update(ref)
    package.add_dependency(Factory.create_dependency("demo", git_config))

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [{"job": "install", "package": pendulum}, {"job": "install", "package": demo}],
    )

    op = ops[1]

    assert op.package.source_type == "git"
    assert op.package.source_reference == ref[list(ref.keys())[0]]
    assert op.package.source_resolved_reference.startswith("9cf87a2")


def test_solver_does_not_trigger_conflict_for_python_constraint_if_python_requirement_is_compatible(
    solver, repo, package
):
    solver.provider.set_package_python_versions("~2.7 || ^3.4")
    package.add_dependency(
        Factory.create_dependency("A", {"version": "^1.0", "python": "^3.6"})
    )

    package_a = get_package("A", "1.0.0")
    package_a.python_versions = ">=3.6"

    repo.add_package(package_a)

    transaction = solver.solve()

    check_solver_result(transaction, [{"job": "install", "package": package_a}])


def test_solver_does_not_trigger_conflict_for_python_constraint_if_python_requirement_is_compatible_multiple(
    solver, repo, package
):
    solver.provider.set_package_python_versions("~2.7 || ^3.4")
    package.add_dependency(
        Factory.create_dependency("A", {"version": "^1.0", "python": "^3.6"})
    )
    package.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "python": "^3.5.3"})
    )

    package_a = get_package("A", "1.0.0")
    package_a.python_versions = ">=3.6"
    package_a.add_dependency(Factory.create_dependency("B", "^1.0"))

    package_b = get_package("B", "1.0.0")
    package_b.python_versions = ">=3.5.3"

    repo.add_package(package_a)
    repo.add_package(package_b)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )


def test_solver_triggers_conflict_for_dependency_python_not_fully_compatible_with_package_python(
    solver, repo, package
):
    solver.provider.set_package_python_versions("~2.7 || ^3.4")
    package.add_dependency(
        Factory.create_dependency("A", {"version": "^1.0", "python": "^3.5"})
    )

    package_a = get_package("A", "1.0.0")
    package_a.python_versions = ">=3.6"

    repo.add_package(package_a)

    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_finds_compatible_package_for_dependency_python_not_fully_compatible_with_package_python(
    solver, repo, package
):
    solver.provider.set_package_python_versions("~2.7 || ^3.4")
    package.add_dependency(
        Factory.create_dependency("A", {"version": "^1.0", "python": "^3.5"})
    )

    package_a101 = get_package("A", "1.0.1")
    package_a101.python_versions = ">=3.6"

    package_a100 = get_package("A", "1.0.0")
    package_a100.python_versions = ">=3.5"

    repo.add_package(package_a100)
    repo.add_package(package_a101)

    transaction = solver.solve()

    check_solver_result(transaction, [{"job": "install", "package": package_a100}])


def test_solver_does_not_trigger_new_resolution_on_duplicate_dependencies_if_only_extras(
    solver, repo, package
):
    dep1 = Dependency.create_from_pep_508('B (>=1.0); extra == "foo"')
    dep1.activate()
    dep2 = Dependency.create_from_pep_508('B (>=2.0); extra == "bar"')
    dep2.activate()

    package.add_dependency(
        Factory.create_dependency("A", {"version": "^1.0", "extras": ["foo", "bar"]})
    )

    package_a = get_package("A", "1.0.0")
    package_a.extras = {"foo": [dep1], "bar": [dep2]}
    package_a.add_dependency(dep1)
    package_a.add_dependency(dep2)

    package_b2 = get_package("B", "2.0.0")
    package_b1 = get_package("B", "1.0.0")

    repo.add_package(package_a)
    repo.add_package(package_b1)
    repo.add_package(package_b2)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_b2},
            {"job": "install", "package": package_a},
        ],
    )

    assert str(ops[0].package.marker) == ""
    assert str(ops[1].package.marker) == ""


def test_solver_does_not_raise_conflict_for_locked_conditional_dependencies(
    solver, repo, package
):
    solver.provider.set_package_python_versions("~2.7 || ^3.4")
    package.add_dependency(
        Factory.create_dependency("A", {"version": "^1.0", "python": "^3.6"})
    )
    package.add_dependency(Factory.create_dependency("B", "^1.0"))

    package_a = get_package("A", "1.0.0")
    package_a.python_versions = ">=3.6"
    package_a.marker = parse_marker(
        'python_version >= "3.6" and python_version < "4.0"'
    )

    package_b = get_package("B", "1.0.0")

    repo.add_package(package_a)
    repo.add_package(package_b)

    solver._locked = Repository([package_a])
    transaction = solver.solve(use_latest=[package_b.name])

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_returns_extras_if_requested_in_dependencies_and_not_in_root_package(
    solver, repo, package
):
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("B", "*"))
    package.add_dependency(Factory.create_dependency("C", "*"))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_d = get_package("D", "1.0")

    package_b.add_dependency(
        Factory.create_dependency("C", {"version": "^1.0", "extras": ["foo"]})
    )

    package_c.add_dependency(
        Factory.create_dependency("D", {"version": "^1.0", "optional": True})
    )
    package_c.extras = {"foo": [Factory.create_dependency("D", "^1.0")]}

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    transaction = solver.solve()

    check_solver_result(
        transaction,
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
    package.add_dependency(Factory.create_dependency("A", "~1.8.0"))
    package.add_dependency(Factory.create_dependency("B", "^0.5.0"))

    package_a185 = get_package("A", "1.8.5")
    package_a19b1 = get_package("A", "1.9b1")
    package_b = get_package("B", "0.5.0")
    package_b.add_dependency(Factory.create_dependency("A", ">=1.9b1"))

    repo.add_package(package_a185)
    repo.add_package(package_a19b1)
    repo.add_package(package_b)

    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_ignores_dependencies_with_incompatible_python_full_version_marker(
    solver, repo, package
):
    solver.provider.set_package_python_versions("^3.6")
    package.add_dependency(Factory.create_dependency("A", "^1.0"))
    package.add_dependency(Factory.create_dependency("B", "^2.0"))

    package_a = get_package("A", "1.0.0")
    package_a.add_dependency(
        Dependency.create_from_pep_508(
            'B (<2.0); platform_python_implementation == "PyPy" and python_full_version < "2.7.9"'
        )
    )

    package_b200 = get_package("B", "2.0.0")
    package_b100 = get_package("B", "1.0.0")

    repo.add_package(package_a)
    repo.add_package(package_b100)
    repo.add_package(package_b200)

    transaction = solver.solve()

    check_solver_result(
        transaction,
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

    demo_installed = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference="master",
        source_resolved_reference="123456",
    )
    demo = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference="master",
        source_resolved_reference="9cf87a285a2d3fbb0b9fa621997b3acc3631ed24",
    )
    installed.add_package(demo_installed)

    package.add_dependency(
        Factory.create_dependency("demo", {"git": "https://github.com/demo/demo.git"})
    )

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": pendulum},
            {"job": "update", "from": demo_installed, "to": demo},
        ],
    )

    op = ops[1]

    assert op.job_type == "update"
    assert op.package.source_type == "git"
    assert op.package.source_reference == "master"
    assert op.package.source_resolved_reference.startswith("9cf87a2")
    assert op.initial_package.source_resolved_reference == "123456"


def test_solver_git_dependencies_update_skipped(solver, repo, package, installed):
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    demo = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference="master",
        source_resolved_reference="9cf87a285a2d3fbb0b9fa621997b3acc3631ed24",
    )
    installed.add_package(demo)

    package.add_dependency(
        Factory.create_dependency("demo", {"git": "https://github.com/demo/demo.git"})
    )

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": pendulum},
            {"job": "install", "package": demo, "skipped": True},
        ],
    )


def test_solver_git_dependencies_short_hash_update_skipped(
    solver, repo, package, installed
):
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    demo = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference="9cf87a285a2d3fbb0b9fa621997b3acc3631ed24",
        source_resolved_reference="9cf87a285a2d3fbb0b9fa621997b3acc3631ed24",
    )
    installed.add_package(demo)

    package.add_dependency(
        Factory.create_dependency(
            "demo", {"git": "https://github.com/demo/demo.git", "rev": "9cf87a2"}
        )
    )

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": pendulum},
            {
                "job": "install",
                "package": Package(
                    "demo",
                    "0.1.2",
                    source_type="git",
                    source_url="https://github.com/demo/demo.git",
                    source_reference="9cf87a285a2d3fbb0b9fa621997b3acc3631ed24",
                    source_resolved_reference="9cf87a285a2d3fbb0b9fa621997b3acc3631ed24",
                ),
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

    package.add_dependency(Factory.create_dependency("demo", {"path": path}))

    transaction = solver.solve()

    demo = Package("demo", "0.1.2", source_type="directory", source_url=path)

    ops = check_solver_result(
        transaction,
        [{"job": "install", "package": pendulum}, {"job": "install", "package": demo}],
    )

    op = ops[1]

    assert op.package.name == "demo"
    assert op.package.version.text == "0.1.2"
    assert op.package.source_type == "directory"
    assert op.package.source_url == path


def test_solver_can_resolve_directory_dependencies_nested_editable(
    solver, repo, pool, installed, locked, io
):
    base = Path(__file__).parent.parent / "fixtures" / "project_with_nested_local"
    poetry = Factory().create_poetry(cwd=base)
    package = poetry.package

    solver = Solver(
        package, pool, installed, locked, io, provider=Provider(package, pool, io)
    )

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {
                "job": "install",
                "package": Package(
                    "quix",
                    "1.2.3",
                    source_type="directory",
                    source_url=(base / "quix").as_posix(),
                ),
                "skipped": False,
            },
            {
                "job": "install",
                "package": Package(
                    "bar",
                    "1.2.3",
                    source_type="directory",
                    source_url=(base / "bar").as_posix(),
                ),
                "skipped": False,
            },
            {
                "job": "install",
                "package": Package(
                    "foo",
                    "1.2.3",
                    source_type="directory",
                    source_url=(base / "foo").as_posix(),
                ),
                "skipped": False,
            },
        ],
    )

    for op in ops:
        assert op.package.source_type == "directory"
        assert op.package.develop is True


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

    package.add_dependency(
        Factory.create_dependency("demo", {"path": path, "extras": ["foo"]})
    )

    transaction = solver.solve()

    demo = Package("demo", "0.1.2", source_type="directory", source_url=path)

    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": cleo},
            {"job": "install", "package": pendulum},
            {"job": "install", "package": demo},
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

    package.add_dependency(Factory.create_dependency("demo", {"path": path}))

    transaction = solver.solve()

    demo = Package("demo", "0.1.0", source_type="file", source_url=path)

    ops = check_solver_result(
        transaction,
        [{"job": "install", "package": pendulum}, {"job": "install", "package": demo}],
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

    package.add_dependency(
        Factory.create_dependency("demo", {"path": path, "extras": ["foo"]})
    )

    transaction = solver.solve()

    demo = Package("demo", "0.1.0", source_type="file", source_url=path)

    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": cleo},
            {"job": "install", "package": pendulum},
            {"job": "install", "package": demo},
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

    package.add_dependency(Factory.create_dependency("demo", {"path": path}))

    transaction = solver.solve()

    demo = Package("demo", "0.1.0", source_type="file", source_url=path)

    ops = check_solver_result(
        transaction,
        [{"job": "install", "package": pendulum}, {"job": "install", "package": demo}],
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

    package.add_dependency(
        Factory.create_dependency("demo", {"path": path, "extras": ["foo"]})
    )

    transaction = solver.solve()

    demo = Package("demo", "0.1.0", source_type="file", source_url=path)

    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": cleo},
            {"job": "install", "package": pendulum},
            {"job": "install", "package": demo},
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

    package.add_dependency(Factory.create_dependency("isort", "4.3.4"))

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {
                "job": "install",
                "package": Package(
                    "futures",
                    "3.2.0",
                    source_type="legacy",
                    source_url=repo.url,
                    source_reference=repo.name,
                ),
            },
            {
                "job": "install",
                "package": Package(
                    "isort",
                    "4.3.4",
                    source_type="legacy",
                    source_url=repo.url,
                    source_reference=repo.name,
                ),
            },
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

    package.add_dependency(Factory.create_dependency("isort", "4.3.4"))

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {
                "job": "install",
                "package": Package(
                    "isort",
                    "4.3.4",
                    source_type="legacy",
                    source_url=repo.url,
                    source_reference=repo.name,
                ),
            }
        ],
    )


def test_solver_skips_invalid_versions(package, installed, locked, io):
    package.python_versions = "^3.7"

    repo = MockPyPIRepository()
    pool = Pool([repo])

    solver = Solver(package, pool, installed, locked, io)

    package.add_dependency(Factory.create_dependency("trackpy", "^0.4"))

    transaction = solver.solve()

    check_solver_result(
        transaction, [{"job": "install", "package": get_package("trackpy", "0.4.1")}]
    )


def test_multiple_constraints_on_root(package, solver, repo):
    package.add_dependency(
        Factory.create_dependency("foo", {"version": "^1.0", "python": "^2.7"})
    )
    package.add_dependency(
        Factory.create_dependency("foo", {"version": "^2.0", "python": "^3.7"})
    )

    foo15 = get_package("foo", "1.5.0")
    foo25 = get_package("foo", "2.5.0")

    repo.add_package(foo15)
    repo.add_package(foo25)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [{"job": "install", "package": foo15}, {"job": "install", "package": foo25}],
    )


def test_solver_chooses_most_recent_version_amongst_repositories(
    package, installed, locked, io
):
    package.python_versions = "^3.7"
    package.add_dependency(Factory.create_dependency("tomlkit", {"version": "^0.5"}))

    repo = MockLegacyRepository()
    pool = Pool([repo, MockPyPIRepository()])

    solver = Solver(package, pool, installed, locked, io)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction, [{"job": "install", "package": get_package("tomlkit", "0.5.3")}]
    )

    assert ops[0].package.source_type is None
    assert ops[0].package.source_url is None


def test_solver_chooses_from_correct_repository_if_forced(
    package, installed, locked, io
):
    package.python_versions = "^3.7"
    package.add_dependency(
        Factory.create_dependency("tomlkit", {"version": "^0.5", "source": "legacy"})
    )

    repo = MockLegacyRepository()
    pool = Pool([repo, MockPyPIRepository()])

    solver = Solver(package, pool, installed, locked, io)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {
                "job": "install",
                "package": Package(
                    "tomlkit",
                    "0.5.2",
                    source_type="legacy",
                    source_url=repo.url,
                    source_reference=repo.name,
                ),
            }
        ],
    )

    assert "http://legacy.foo.bar" == ops[0].package.source_url


def test_solver_chooses_from_correct_repository_if_forced_and_transitive_dependency(
    package, installed, locked, io
):
    package.python_versions = "^3.7"
    package.add_dependency(Factory.create_dependency("foo", "^1.0"))
    package.add_dependency(
        Factory.create_dependency("tomlkit", {"version": "^0.5", "source": "legacy"})
    )

    repo = Repository()
    foo = get_package("foo", "1.0.0")
    foo.add_dependency(Factory.create_dependency("tomlkit", "^0.5.0"))
    repo.add_package(foo)
    pool = Pool([MockLegacyRepository(), repo, MockPyPIRepository()])

    solver = Solver(package, pool, installed, locked, io)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {
                "job": "install",
                "package": Package(
                    "tomlkit",
                    "0.5.2",
                    source_type="legacy",
                    source_url="http://legacy.foo.bar",
                    source_reference="legacy",
                ),
            },
            {"job": "install", "package": foo},
        ],
    )

    assert "http://legacy.foo.bar" == ops[0].package.source_url

    assert ops[1].package.source_type is None
    assert ops[1].package.source_url is None


def test_solver_does_not_choose_from_secondary_repository_by_default(
    package, installed, locked, io
):
    package.python_versions = "^3.7"
    package.add_dependency(Factory.create_dependency("clikit", {"version": "^0.2.0"}))

    pool = Pool()
    pool.add_repository(MockPyPIRepository(), secondary=True)
    pool.add_repository(MockLegacyRepository())

    solver = Solver(package, pool, installed, locked, io)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {
                "job": "install",
                "package": Package(
                    "pastel",
                    "0.1.0",
                    source_type="legacy",
                    source_url="http://legacy.foo.bar",
                    source_reference="legacy",
                ),
            },
            {"job": "install", "package": get_package("pylev", "1.3.0")},
            {
                "job": "install",
                "package": Package(
                    "clikit",
                    "0.2.4",
                    source_type="legacy",
                    source_url="http://legacy.foo.bar",
                    source_reference="legacy",
                ),
            },
        ],
    )

    assert "http://legacy.foo.bar" == ops[0].package.source_url
    assert ops[1].package.source_type is None
    assert ops[1].package.source_url is None
    assert "http://legacy.foo.bar" == ops[2].package.source_url


def test_solver_chooses_from_secondary_if_explicit(package, installed, locked, io):
    package.python_versions = "^3.7"
    package.add_dependency(
        Factory.create_dependency("clikit", {"version": "^0.2.0", "source": "PyPI"})
    )

    pool = Pool()
    pool.add_repository(MockPyPIRepository(), secondary=True)
    pool.add_repository(MockLegacyRepository())

    solver = Solver(package, pool, installed, locked, io)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {
                "job": "install",
                "package": Package(
                    "pastel",
                    "0.1.0",
                    source_type="legacy",
                    source_url="http://legacy.foo.bar",
                    source_reference="legacy",
                ),
            },
            {"job": "install", "package": get_package("pylev", "1.3.0")},
            {"job": "install", "package": get_package("clikit", "0.2.4")},
        ],
    )

    assert "http://legacy.foo.bar" == ops[0].package.source_url
    assert ops[1].package.source_type is None
    assert ops[1].package.source_url is None
    assert ops[2].package.source_type is None
    assert ops[2].package.source_url is None


def test_solver_discards_packages_with_empty_markers(
    package, installed, locked, io, pool, repo
):
    package.python_versions = "~2.7 || ^3.4"
    package.add_dependency(
        Factory.create_dependency(
            "a", {"version": "^0.1.0", "markers": "python_version >= '3.4'"}
        )
    )

    package_a = get_package("a", "0.1.0")
    package_a.add_dependency(
        Factory.create_dependency(
            "b", {"version": "^0.1.0", "markers": "python_version < '3.2'"}
        )
    )
    package_a.add_dependency(Factory.create_dependency("c", "^0.2.0"))
    package_b = get_package("b", "0.1.0")
    package_c = get_package("c", "0.2.0")
    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    solver = Solver(package, pool, installed, locked, io)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_a},
        ],
    )


def test_solver_does_not_raise_conflict_for_conditional_dev_dependencies(
    solver, repo, package
):
    solver.provider.set_package_python_versions("~2.7 || ^3.5")
    package.add_dependency(
        Factory.create_dependency(
            "A", {"version": "^1.0", "python": "~2.7"}, groups=["dev"]
        )
    )
    package.add_dependency(
        Factory.create_dependency(
            "A", {"version": "^2.0", "python": "^3.5"}, groups=["dev"]
        )
    )

    package_a100 = get_package("A", "1.0.0")
    package_a200 = get_package("A", "2.0.0")

    repo.add_package(package_a100)
    repo.add_package(package_a200)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_a100},
            {"job": "install", "package": package_a200},
        ],
    )


def test_solver_does_not_loop_indefinitely_on_duplicate_constraints_with_extras(
    solver, repo, package
):
    solver.provider.set_package_python_versions("~2.7 || ^3.5")
    package.add_dependency(
        Factory.create_dependency(
            "requests", {"version": "^2.22.0", "extras": ["security"]}
        )
    )

    requests = get_package("requests", "2.22.0")
    requests.add_dependency(Factory.create_dependency("idna", ">=2.5,<2.9"))
    requests.add_dependency(
        Factory.create_dependency(
            "idna", {"version": ">=2.0.0", "markers": "extra == 'security'"}
        )
    )
    requests.extras["security"] = [get_dependency("idna", ">=2.0.0")]
    idna = get_package("idna", "2.8")

    repo.add_package(requests)
    repo.add_package(idna)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [{"job": "install", "package": idna}, {"job": "install", "package": requests}],
    )


def test_solver_does_not_fail_with_locked_git_and_non_git_dependencies(
    solver, repo, package, locked, pool, installed, io
):
    package.add_dependency(
        Factory.create_dependency("demo", {"git": "https://github.com/demo/demo.git"})
    )
    package.add_dependency(Factory.create_dependency("a", "^1.2.3"))

    git_package = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference="master",
        source_resolved_reference="commit",
    )

    installed.add_package(git_package)

    locked.add_package(get_package("a", "1.2.3"))
    locked.add_package(git_package)

    repo.add_package(get_package("a", "1.2.3"))
    repo.add_package(Package("pendulum", "2.1.2"))

    solver = Solver(package, pool, installed, locked, io)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": get_package("a", "1.2.3")},
            {"job": "install", "package": git_package, "skipped": True},
        ],
    )


def test_ignore_python_constraint_no_overlap_dependencies(solver, repo, package):
    pytest = get_package("demo", "1.0.0")
    pytest.add_dependency(
        Factory.create_dependency(
            "configparser", {"version": "^1.2.3", "python": "<3.2"}
        )
    )

    package.add_dependency(
        Factory.create_dependency("demo", {"version": "^1.0.0", "python": "^3.6"})
    )

    repo.add_package(pytest)
    repo.add_package(get_package("configparser", "1.2.3"))

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [{"job": "install", "package": pytest}],
    )


def test_solver_should_not_go_into_an_infinite_loop_on_duplicate_dependencies(
    solver, repo, package
):
    solver.provider.set_package_python_versions("~2.7 || ^3.5")
    package.add_dependency(Factory.create_dependency("A", "^1.0"))

    package_a = get_package("A", "1.0.0")
    package_a.add_dependency(Factory.create_dependency("B", "*"))
    package_a.add_dependency(
        Factory.create_dependency(
            "B", {"version": "^1.0", "markers": "implementation_name == 'pypy'"}
        )
    )

    package_b20 = get_package("B", "2.0.0")
    package_b10 = get_package("B", "1.0.0")

    repo.add_package(package_a)
    repo.add_package(package_b10)
    repo.add_package(package_b20)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_b10},
            {"job": "install", "package": package_b20},
            {"job": "install", "package": package_a},
        ],
    )


def test_solver_synchronize_single(package, pool, installed, locked, io):
    solver = Solver(package, pool, installed, locked, io)
    package_a = get_package("a", "1.0")
    installed.add_package(package_a)

    transaction = solver.solve()

    check_solver_result(
        transaction, [{"job": "remove", "package": package_a}], synchronize=True
    )


@pytest.mark.skip(reason="Poetry no longer has critical package requirements")
def test_solver_with_synchronization_keeps_critical_package(
    package, pool, installed, locked, io
):
    solver = Solver(package, pool, installed, locked, io)
    package_pip = get_package("setuptools", "1.0")
    installed.add_package(package_pip)

    transaction = solver.solve()

    check_solver_result(transaction, [])


def test_solver_cannot_choose_another_version_for_directory_dependencies(
    solver, repo, package
):
    pendulum = get_package("pendulum", "2.0.3")
    demo = get_package("demo", "0.1.0")
    foo = get_package("foo", "1.2.3")
    foo.add_dependency(Factory.create_dependency("demo", "<0.1.2"))
    repo.add_package(foo)
    repo.add_package(demo)
    repo.add_package(pendulum)

    path = (
        Path(__file__).parent.parent
        / "fixtures"
        / "git"
        / "github.com"
        / "demo"
        / "demo"
    ).as_posix()

    package.add_dependency(Factory.create_dependency("demo", {"path": path}))
    package.add_dependency(Factory.create_dependency("foo", "^1.2.3"))

    # This is not solvable since the demo version is pinned
    # via the directory dependency
    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_cannot_choose_another_version_for_file_dependencies(
    solver, repo, package
):
    pendulum = get_package("pendulum", "2.0.3")
    demo = get_package("demo", "0.0.8")
    foo = get_package("foo", "1.2.3")
    foo.add_dependency(Factory.create_dependency("demo", "<0.1.0"))
    repo.add_package(foo)
    repo.add_package(demo)
    repo.add_package(pendulum)

    path = (
        Path(__file__).parent.parent
        / "fixtures"
        / "distributions"
        / "demo-0.1.0-py2.py3-none-any.whl"
    ).as_posix()

    package.add_dependency(Factory.create_dependency("demo", {"path": path}))
    package.add_dependency(Factory.create_dependency("foo", "^1.2.3"))

    # This is not solvable since the demo version is pinned
    # via the file dependency
    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_cannot_choose_another_version_for_git_dependencies(
    solver, repo, package
):
    pendulum = get_package("pendulum", "2.0.3")
    demo = get_package("demo", "0.0.8")
    foo = get_package("foo", "1.2.3")
    foo.add_dependency(Factory.create_dependency("demo", "<0.1.0"))
    repo.add_package(foo)
    repo.add_package(demo)
    repo.add_package(pendulum)

    package.add_dependency(
        Factory.create_dependency("demo", {"git": "https://github.com/demo/demo.git"})
    )
    package.add_dependency(Factory.create_dependency("foo", "^1.2.3"))

    # This is not solvable since the demo version is pinned
    # via the file dependency
    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_cannot_choose_another_version_for_url_dependencies(
    solver, repo, package, http
):
    path = (
        Path(__file__).parent.parent
        / "fixtures"
        / "distributions"
        / "demo-0.1.0-py2.py3-none-any.whl"
    )

    http.register_uri(
        "GET",
        "https://foo.bar/demo-0.1.0-py2.py3-none-any.whl",
        body=path.read_bytes(),
        streaming=True,
    )
    pendulum = get_package("pendulum", "2.0.3")
    demo = get_package("demo", "0.0.8")
    foo = get_package("foo", "1.2.3")
    foo.add_dependency(Factory.create_dependency("demo", "<0.1.0"))
    repo.add_package(foo)
    repo.add_package(demo)
    repo.add_package(pendulum)

    package.add_dependency(
        Factory.create_dependency(
            "demo",
            {"url": "https://foo.bar/distributions/demo-0.1.0-py2.py3-none-any.whl"},
        )
    )
    package.add_dependency(Factory.create_dependency("foo", "^1.2.3"))

    # This is not solvable since the demo version is pinned
    # via the git dependency
    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_should_not_update_same_version_packages_if_installed_has_no_source_type(
    solver, repo, package, installed
):
    package.add_dependency(Factory.create_dependency("foo", "1.0.0"))

    foo = Package(
        "foo",
        "1.0.0",
        source_type="legacy",
        source_url="https://foo.bar",
        source_reference="custom",
    )
    repo.add_package(foo)
    installed.add_package(get_package("foo", "1.0.0"))

    transaction = solver.solve()

    check_solver_result(
        transaction, [{"job": "install", "package": foo, "skipped": True}]
    )


def test_solver_should_use_the_python_constraint_from_the_environment_if_available(
    solver, repo, package, installed
):
    solver.provider.set_package_python_versions("~2.7 || ^3.5")
    package.add_dependency(Factory.create_dependency("A", "^1.0"))

    a = get_package("A", "1.0.0")
    a.add_dependency(
        Factory.create_dependency(
            "B", {"version": "^1.0.0", "markers": 'python_version < "3.2"'}
        )
    )
    b = get_package("B", "1.0.0")
    b.python_versions = ">=2.6, <3"

    repo.add_package(a)
    repo.add_package(b)

    with solver.use_environment(MockEnv((2, 7, 18))):
        transaction = solver.solve()

    check_solver_result(
        transaction,
        [{"job": "install", "package": b}, {"job": "install", "package": a}],
    )


def test_solver_should_resolve_all_versions_for_multiple_duplicate_dependencies(
    solver, repo, package
):
    package.python_versions = "~2.7 || ^3.5"
    package.add_dependency(
        Factory.create_dependency(
            "A", {"version": "^1.0", "markers": "python_version < '3.5'"}
        )
    )
    package.add_dependency(
        Factory.create_dependency(
            "A", {"version": "^2.0", "markers": "python_version >= '3.5'"}
        )
    )
    package.add_dependency(
        Factory.create_dependency(
            "B", {"version": "^3.0", "markers": "python_version < '3.5'"}
        )
    )
    package.add_dependency(
        Factory.create_dependency(
            "B", {"version": "^4.0", "markers": "python_version >= '3.5'"}
        )
    )

    package_a10 = get_package("A", "1.0.0")
    package_a20 = get_package("A", "2.0.0")
    package_b30 = get_package("B", "3.0.0")
    package_b40 = get_package("B", "4.0.0")

    repo.add_package(package_a10)
    repo.add_package(package_a20)
    repo.add_package(package_b30)
    repo.add_package(package_b40)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_a10},
            {"job": "install", "package": package_a20},
            {"job": "install", "package": package_b30},
            {"job": "install", "package": package_b40},
        ],
    )


def test_solver_should_not_raise_errors_for_irrelevant_python_constraints(
    solver, repo, package
):
    package.python_versions = "^3.6"
    solver.provider.set_package_python_versions("^3.6")
    package.add_dependency(
        Factory.create_dependency("dataclasses", {"version": "^0.7", "python": "<3.7"})
    )

    dataclasses = get_package("dataclasses", "0.7")
    dataclasses.python_versions = ">=3.6, <3.7"

    repo.add_package(dataclasses)
    transaction = solver.solve()

    check_solver_result(transaction, [{"job": "install", "package": dataclasses}])


def test_solver_can_resolve_transitive_extras(solver, repo, package):
    package.add_dependency(Factory.create_dependency("requests", "^2.24.0"))
    package.add_dependency(Factory.create_dependency("PyOTA", "^2.1.0"))

    requests = get_package("requests", "2.24.0")
    requests.add_dependency(Factory.create_dependency("certifi", ">=2017.4.17"))
    dep = get_dependency("PyOpenSSL", ">=0.14")
    requests.add_dependency(
        Factory.create_dependency("PyOpenSSL", {"version": ">=0.14", "optional": True})
    )
    requests.extras["security"] = [dep]
    pyota = get_package("PyOTA", "2.1.0")
    pyota.add_dependency(
        Factory.create_dependency(
            "requests", {"version": ">=2.24.0", "extras": ["security"]}
        )
    )

    repo.add_package(requests)
    repo.add_package(pyota)
    repo.add_package(get_package("certifi", "2017.4.17"))
    repo.add_package(get_package("pyopenssl", "0.14"))

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": get_package("certifi", "2017.4.17")},
            {"job": "install", "package": get_package("pyopenssl", "0.14")},
            {"job": "install", "package": requests},
            {"job": "install", "package": pyota},
        ],
    )


def test_solver_can_resolve_for_packages_with_missing_extras(solver, repo, package):
    package.add_dependency(
        Factory.create_dependency(
            "django-anymail", {"version": "^6.0", "extras": ["postmark"]}
        )
    )

    django_anymail = get_package("django-anymail", "6.1.0")
    django_anymail.add_dependency(Factory.create_dependency("django", ">=2.0"))
    django_anymail.add_dependency(Factory.create_dependency("requests", ">=2.4.3"))
    django_anymail.add_dependency(
        Factory.create_dependency("boto3", {"version": "*", "optional": True})
    )
    django_anymail.extras["amazon_ses"] = [Factory.create_dependency("boto3", "*")]
    django = get_package("django", "2.2.0")
    boto3 = get_package("boto3", "1.0.0")
    requests = get_package("requests", "2.24.0")

    repo.add_package(django_anymail)
    repo.add_package(django)
    repo.add_package(boto3)
    repo.add_package(requests)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": django},
            {"job": "install", "package": requests},
            {"job": "install", "package": django_anymail},
        ],
    )


def test_solver_can_resolve_python_restricted_package_dependencies(
    solver, repo, package, locked
):
    package.add_dependency(
        Factory.create_dependency("futures", {"version": "^3.3.0", "python": "~2.7"})
    )
    package.add_dependency(
        Factory.create_dependency("pre-commit", {"version": "^2.6", "python": "^3.6.1"})
    )

    futures = Package("futures", "3.3.0")
    futures.python_versions = ">=2.6, <3"

    pre_commit = Package("pre-commit", "2.7.1")
    pre_commit.python_versions = ">=3.6.1"

    locked.add_package(futures)
    locked.add_package(pre_commit)

    repo.add_package(futures)
    repo.add_package(pre_commit)

    transaction = solver.solve(use_latest=["pre-commit"])

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": futures},
            {"job": "install", "package": pre_commit},
        ],
    )


def test_solver_should_not_raise_errors_for_irrelevant_transitive_python_constraints(
    solver, repo, package
):
    package.python_versions = "~2.7 || ^3.5"
    solver.provider.set_package_python_versions("~2.7 || ^3.5")
    package.add_dependency(Factory.create_dependency("virtualenv", "^20.4.3"))
    package.add_dependency(
        Factory.create_dependency("pre-commit", {"version": "^2.6", "python": "^3.6.1"})
    )

    virtualenv = get_package("virtualenv", "20.4.3")
    virtualenv.python_versions = "!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,>=2.7"
    virtualenv.add_dependency(
        Factory.create_dependency(
            "importlib-resources", {"version": "*", "markers": 'python_version < "3.7"'}
        )
    )

    pre_commit = Package("pre-commit", "2.7.1")
    pre_commit.python_versions = ">=3.6.1"
    pre_commit.add_dependency(
        Factory.create_dependency(
            "importlib-resources", {"version": "*", "markers": 'python_version < "3.7"'}
        )
    )

    importlib_resources = get_package("importlib-resources", "5.1.2")
    importlib_resources.python_versions = ">=3.6"

    importlib_resources_3_2_1 = get_package("importlib-resources", "3.2.1")
    importlib_resources_3_2_1.python_versions = (
        "!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,!=3.4.*,>=2.7"
    )

    repo.add_package(virtualenv)
    repo.add_package(pre_commit)
    repo.add_package(importlib_resources)
    repo.add_package(importlib_resources_3_2_1)
    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": importlib_resources_3_2_1},
            {"job": "install", "package": pre_commit},
            {"job": "install", "package": virtualenv},
        ],
    )
