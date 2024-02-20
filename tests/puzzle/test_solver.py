from __future__ import annotations

import re

from typing import TYPE_CHECKING
from typing import Any

import pytest

from cleo.io.buffered_io import BufferedIO
from cleo.io.null_io import NullIO
from packaging.utils import canonicalize_name
from poetry.core.packages.dependency import Dependency
from poetry.core.packages.package import Package
from poetry.core.packages.project_package import ProjectPackage
from poetry.core.packages.vcs_dependency import VCSDependency
from poetry.core.version.markers import parse_marker

from poetry.factory import Factory
from poetry.installation.operations import Update
from poetry.packages import DependencyPackage
from poetry.puzzle import Solver
from poetry.puzzle.exceptions import SolverProblemError
from poetry.puzzle.provider import IncompatibleConstraintsError
from poetry.repositories.repository import Repository
from poetry.repositories.repository_pool import Priority
from poetry.repositories.repository_pool import RepositoryPool
from poetry.utils.env import MockEnv
from tests.helpers import MOCK_DEFAULT_GIT_REVISION
from tests.helpers import get_dependency
from tests.helpers import get_package
from tests.repositories.test_legacy_repository import (
    MockRepository as MockLegacyRepository,
)
from tests.repositories.test_pypi_repository import MockRepository as MockPyPIRepository


if TYPE_CHECKING:
    import httpretty

    from pytest_mock import MockerFixture

    from poetry.installation.operations.operation import Operation
    from poetry.puzzle.provider import Provider
    from poetry.puzzle.transaction import Transaction
    from tests.types import FixtureDirGetter

DEFAULT_SOURCE_REF = (
    VCSDependency("poetry", "git", "git@github.com:python-poetry/poetry.git").branch
    or "HEAD"
)


def set_package_python_versions(provider: Provider, python_versions: str) -> None:
    provider._package.python_versions = python_versions
    provider._python_constraint = provider._package.python_constraint


@pytest.fixture()
def io() -> NullIO:
    return NullIO()


@pytest.fixture()
def package() -> ProjectPackage:
    return ProjectPackage("root", "1.0")


@pytest.fixture()
def repo() -> Repository:
    return Repository("repo")


@pytest.fixture()
def pool(repo: Repository) -> RepositoryPool:
    return RepositoryPool([repo])


@pytest.fixture()
def solver(package: ProjectPackage, pool: RepositoryPool, io: NullIO) -> Solver:
    return Solver(package, pool, [], [], io)


def check_solver_result(
    transaction: Transaction,
    expected: list[dict[str, Any]],
    synchronize: bool = False,
) -> list[Operation]:
    for e in expected:
        if "skipped" not in e:
            e["skipped"] = False

    result = []
    ops = transaction.calculate_operations(synchronize=synchronize)
    for op in ops:
        if op.job_type == "update":
            assert isinstance(op, Update)
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

    return ops


def test_solver_install_single(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    repo.add_package(package_a)

    transaction = solver.solve([get_dependency("A").name])

    check_solver_result(transaction, [{"job": "install", "package": package_a}])


def test_solver_remove_if_no_longer_locked(
    package: ProjectPackage, pool: RepositoryPool, io: NullIO
) -> None:
    package_a = get_package("A", "1.0")

    solver = Solver(package, pool, [package_a], [package_a], io)
    transaction = solver.solve()

    check_solver_result(transaction, [{"job": "remove", "package": package_a}])


def test_remove_non_installed(
    package: ProjectPackage, repo: Repository, pool: RepositoryPool, io: NullIO
) -> None:
    package_a = get_package("A", "1.0")
    repo.add_package(package_a)

    solver = Solver(package, pool, [], [package_a], io)
    transaction = solver.solve([])

    check_solver_result(transaction, [])


def test_install_non_existing_package_fail(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.add_dependency(Factory.create_dependency("B", "1"))

    package_a = get_package("A", "1.0")
    repo.add_package(package_a)

    with pytest.raises(SolverProblemError):
        solver.solve()


def test_install_unpublished_package_does_not_fail(
    package: ProjectPackage, repo: Repository, pool: RepositoryPool, io: NullIO
) -> None:
    package.add_dependency(Factory.create_dependency("B", "1"))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1")
    package_b.add_dependency(Factory.create_dependency("A", "1.0"))

    repo.add_package(package_a)

    solver = Solver(package, pool, [package_b], [], io)
    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_a},
            {
                "job": "install",
                "package": package_b,
                "skipped": True,  # already installed
            },
        ],
    )


def test_solver_with_deps(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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


def test_install_honours_not_equal(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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


def test_install_with_deps_in_order(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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


def test_install_installed(
    package: ProjectPackage, repo: Repository, pool: RepositoryPool, io: NullIO
) -> None:
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    repo.add_package(package_a)

    solver = Solver(package, pool, [package_a], [], io)
    transaction = solver.solve()

    check_solver_result(
        transaction, [{"job": "install", "package": package_a, "skipped": True}]
    )


def test_update_installed(
    package: ProjectPackage, repo: Repository, pool: RepositoryPool, io: NullIO
) -> None:
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    new_package_a = get_package("A", "1.1")
    repo.add_package(package_a)
    repo.add_package(new_package_a)

    solver = Solver(package, pool, [get_package("A", "1.0")], [], io)
    transaction = solver.solve()

    check_solver_result(
        transaction, [{"job": "update", "from": package_a, "to": new_package_a}]
    )


def test_update_with_use_latest(
    package: ProjectPackage, repo: Repository, pool: RepositoryPool, io: NullIO
) -> None:
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("B", "*"))

    package_a = get_package("A", "1.0")
    new_package_a = get_package("A", "1.1")
    package_b = get_package("B", "1.0")
    new_package_b = get_package("B", "1.1")
    repo.add_package(package_a)
    repo.add_package(new_package_a)
    repo.add_package(package_b)
    repo.add_package(new_package_b)

    installed = [get_package("A", "1.0")]
    locked = [package_a, package_b]

    solver = Solver(package, pool, installed, locked, io)
    transaction = solver.solve(use_latest=[package_b.name])

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_a, "skipped": True},
            {"job": "install", "package": new_package_b},
        ],
    )


def test_solver_sets_groups(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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

    _ = check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_respects_root_package_python_versions(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "~3.4")
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


def test_solver_fails_if_mismatch_root_python_versions(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "^3.4")
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


def test_solver_ignores_python_restricted_if_mismatch_root_package_python_versions(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "~3.8")
    package.add_dependency(
        Factory.create_dependency("A", {"version": "1.0", "python": "<3.8"})
    )
    package.add_dependency(
        Factory.create_dependency(
            "B", {"version": "1.0", "markers": "python_version < '3.8'"}
        )
    )

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")

    repo.add_package(package_a)
    repo.add_package(package_b)

    transaction = solver.solve()

    check_solver_result(transaction, [])


def test_solver_solves_optional_and_compatible_packages(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "~3.4")
    package.extras = {canonicalize_name("foo"): [get_dependency("B")]}
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


def test_solver_does_not_return_extras_if_not_requested(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("B", "*"))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")

    package_b.extras = {canonicalize_name("foo"): [get_dependency("C", "^1.0")]}

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


def test_solver_returns_extras_if_requested(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(
        Factory.create_dependency("B", {"version": "*", "extras": ["foo"]})
    )

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")

    dep = get_dependency("C", "^1.0", optional=True)
    dep.marker = parse_marker("extra == 'foo'")
    package_b.extras = {canonicalize_name("foo"): [dep]}
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


@pytest.mark.parametrize("enabled_extra", ["one", "two", None])
def test_solver_returns_extras_only_requested(
    solver: Solver,
    repo: Repository,
    package: ProjectPackage,
    enabled_extra: str | None,
) -> None:
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
    dep10._in_extras = [canonicalize_name("one")]
    dep10.marker = parse_marker("extra == 'one'")

    dep20 = get_dependency("C", "2.0", optional=True)
    dep20._in_extras = [canonicalize_name("two")]
    dep20.marker = parse_marker("extra == 'two'")

    package_b.extras = {
        canonicalize_name("one"): [dep10],
        canonicalize_name("two"): [dep20],
    }

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


@pytest.mark.parametrize("enabled_extra", ["one", "two", None])
def test_solver_returns_extras_when_multiple_extras_use_same_dependency(
    solver: Solver,
    repo: Repository,
    package: ProjectPackage,
    enabled_extra: bool | None,
) -> None:
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")

    dep = get_dependency("C", "*", optional=True)
    dep._in_extras = [canonicalize_name("one"), canonicalize_name("two")]

    package_b.extras = {
        canonicalize_name("one"): [dep],
        canonicalize_name("two"): [dep],
    }

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


@pytest.mark.parametrize("enabled_extra", ["one", "two", None])
def test_solver_returns_extras_only_requested_nested(
    solver: Solver,
    repo: Repository,
    package: ProjectPackage,
    enabled_extra: str | None,
) -> None:
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c10 = get_package("C", "1.0")
    package_c20 = get_package("C", "2.0")

    dep10 = get_dependency("C", "1.0", optional=True)
    dep10._in_extras = [canonicalize_name("one")]
    dep10.marker = parse_marker("extra == 'one'")

    dep20 = get_dependency("C", "2.0", optional=True)
    dep20._in_extras = [canonicalize_name("two")]
    dep20.marker = parse_marker("extra == 'two'")

    package_b.extras = {
        canonicalize_name("one"): [dep10],
        canonicalize_name("two"): [dep20],
    }

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


def test_solver_finds_extras_next_to_non_extras(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    # Root depends on A[foo]
    package.add_dependency(
        Factory.create_dependency("A", {"version": "*", "extras": ["foo"]})
    )

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_d = get_package("D", "1.0")

    # A depends on B; A[foo] depends on B[bar].
    package_a.add_dependency(Factory.create_dependency("B", "*"))
    package_a.add_dependency(
        Factory.create_dependency(
            "B", {"version": "*", "extras": ["bar"], "markers": "extra == 'foo'"}
        )
    )
    package_a.extras = {canonicalize_name("foo"): [get_dependency("B", "*")]}

    # B depends on C; B[bar] depends on D.
    package_b.add_dependency(Factory.create_dependency("C", "*"))
    package_b.add_dependency(
        Factory.create_dependency("D", {"version": "*", "markers": 'extra == "bar"'})
    )
    package_b.extras = {canonicalize_name("bar"): [get_dependency("D", "*")]}

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_d},
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )


def test_solver_merge_extras_into_base_package_multiple_repos_fixes_5727(
    solver: Solver, repo: Repository, pool: RepositoryPool, package: ProjectPackage
) -> None:
    package.add_dependency(
        Factory.create_dependency("A", {"version": "*", "source": "legacy"})
    )
    package.add_dependency(Factory.create_dependency("B", {"version": "*"}))

    package_a = get_package("A", "1.0")
    package_a.extras = {canonicalize_name("foo"): []}

    repo.add_package(package_a)

    package_b = Package("B", "1.0", source_type="legacy")
    package_b.add_dependency(package_a.with_features(["foo"]).to_dependency())

    package_a = Package("A", "1.0", source_type="legacy")
    package_a.extras = {canonicalize_name("foo"): []}

    repo = Repository("legacy")
    repo.add_package(package_a)
    repo.add_package(package_b)

    pool.add_repository(repo)

    transaction = solver.solve()

    ops = transaction.calculate_operations(synchronize=True)

    assert len(ops[0].package.requires) == 0, "a should not require itself"


def test_solver_returns_extras_if_excluded_by_markers_without_extras(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.add_dependency(
        Factory.create_dependency("A", {"version": "*", "extras": ["foo"]})
    )

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")

    # mandatory dependency with marker
    dep = get_dependency("B", "^1.0")
    dep.marker = parse_marker("sys_platform != 'linux'")
    package_a.add_dependency(dep)

    # optional dependency with same constraint and no marker except for extra
    dep = get_dependency("B", "^1.0", optional=True)
    dep.marker = parse_marker("extra == 'foo'")
    package_a.extras = {canonicalize_name("foo"): [dep]}
    package_a.add_dependency(dep)

    repo.add_package(package_a)
    repo.add_package(package_b)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )
    assert (
        str(ops[1].package.requires[0].marker)
        == 'sys_platform != "linux" or extra == "foo"'
    )


def test_solver_returns_prereleases_if_requested(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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


def test_solver_does_not_return_prereleases_if_not_requested(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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


def test_solver_sub_dependencies_with_requirements(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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


def test_solver_sub_dependencies_with_requirements_complex(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "^3.5")
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
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "^3.4")

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


def test_solver_with_dependency_in_both_main_and_dev_dependencies(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "^3.5")
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(
        Factory.create_dependency(
            "A", {"version": "*", "extras": ["foo"]}, groups=["dev"]
        )
    )

    package_a = get_package("A", "1.0")
    package_a.extras = {canonicalize_name("foo"): [get_dependency("C")]}
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

    _ = check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_d},
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_a},
        ],
    )


def test_solver_with_dependency_in_both_main_and_dev_dependencies_with_one_more_dependent(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("E", "*"))
    package.add_dependency(
        Factory.create_dependency(
            "A", {"version": "*", "extras": ["foo"]}, groups=["dev"]
        )
    )

    package_a = get_package("A", "1.0")
    package_a.extras = {canonicalize_name("foo"): [get_dependency("C")]}
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

    _ = check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_d},
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_e},
        ],
    )


def test_solver_with_dependency_and_prerelease_sub_dependencies(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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


def test_solver_with_dependency_and_prerelease_sub_dependencies_increasing_constraints(
    solver: Solver,
    repo: Repository,
    package: ProjectPackage,
    mocker: MockerFixture,
) -> None:
    """Regression test to ensure the solver eventually uses pre-release
    dependencies if the package is progressively constrained enough.

    This is different from test_solver_with_dependency_and_prerelease_sub_dependencies
    above because it also has a wildcard dependency on B at the root level.
    This causes the solver to first narrow B's candidate versions down to
    {0.9.0} at an early level, then eventually down to the empty set once A's
    dependencies are processed at a later level.

    Once the candidate version set is narrowed down to the empty set, the
    solver should re-evaluate available candidate versions from the source, but
    include pre-release versions this time as there are no other options.
    """
    # Note: The order matters here; B must be added before A or the solver
    # evaluates A first and we don't encounter the issue. This is a bit
    # fragile, but the mock call assertions ensure this ordering is maintained.
    package.add_dependency(Factory.create_dependency("B", "*"))
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_a.add_dependency(Factory.create_dependency("B", ">0.9.0"))

    repo.add_package(package_a)
    repo.add_package(get_package("B", "0.9.0"))
    package_b = get_package("B", "1.0.0.dev4")
    repo.add_package(package_b)

    search_for_spy = mocker.spy(solver._provider, "search_for")
    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )

    # The assertions below aren't really the point of this test, but are just
    # being used to ensure the dependency resolution ordering remains the same.
    search_calls = [
        call.args[0]
        for call in search_for_spy.mock_calls
        if call.args[0].name in ("a", "b")
    ]
    assert search_calls == [
        Dependency("a", "*"),
        Dependency("b", "*"),
        Dependency("b", ">0.9.0"),
    ]


def test_solver_circular_dependency(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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

    _ = check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )


def test_solver_circular_dependency_chain(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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

    _ = check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_d},
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_b},
            {"job": "install", "package": package_a},
        ],
    )


def test_solver_dense_dependencies(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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


def test_solver_duplicate_dependencies_same_constraint(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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


def test_solver_duplicate_dependencies_different_constraints(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_a.add_dependency(Factory.create_dependency("B", {"version": "^1.0"}))
    package_a.add_dependency(Factory.create_dependency("B", {"version": "^2.0"}))

    package_b10 = get_package("B", "1.0")
    package_b20 = get_package("B", "2.0")

    repo.add_package(package_a)
    repo.add_package(package_b10)
    repo.add_package(package_b20)

    with pytest.raises(IncompatibleConstraintsError) as e:
        solver.solve()

    expected = """\
Incompatible constraints in requirements of a (1.0):
B (>=1.0,<2.0)
B (>=2.0,<3.0)"""

    assert str(e.value) == expected


def test_solver_duplicate_dependencies_different_constraints_merge_by_marker(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "python": "<3.4"})
    )
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^2.0", "python": ">=3.4"})
    )
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "!=1.1", "python": "<3.4"})
    )

    package_b10 = get_package("B", "1.0")
    package_b11 = get_package("B", "1.1")
    package_b20 = get_package("B", "2.0")

    repo.add_package(package_a)
    repo.add_package(package_b10)
    repo.add_package(package_b11)
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


@pytest.mark.parametrize("git_first", [False, True])
def test_solver_duplicate_dependencies_different_sources_direct_origin_preserved(
    solver: Solver, repo: Repository, package: ProjectPackage, git_first: bool
) -> None:
    pendulum = get_package("pendulum", "2.0.3")
    repo.add_package(pendulum)
    repo.add_package(get_package("cleo", "1.0.0"))
    repo.add_package(get_package("demo", "0.1.0"))

    dependency_pypi = Factory.create_dependency("demo", ">=0.1.0")
    dependency_git = Factory.create_dependency(
        "demo", {"git": "https://github.com/demo/demo.git"}, groups=["dev"]
    )
    if git_first:
        package.add_dependency(dependency_git)
        package.add_dependency(dependency_pypi)
    else:
        package.add_dependency(dependency_pypi)
        package.add_dependency(dependency_git)

    demo = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference=DEFAULT_SOURCE_REF,
        source_resolved_reference=MOCK_DEFAULT_GIT_REVISION,
    )

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [{"job": "install", "package": pendulum}, {"job": "install", "package": demo}],
    )

    op = ops[1]

    assert op.package.source_type == demo.source_type
    assert op.package.source_reference == DEFAULT_SOURCE_REF
    assert op.package.source_resolved_reference is not None
    assert demo.source_resolved_reference is not None
    assert op.package.source_resolved_reference.startswith(
        demo.source_resolved_reference
    )

    complete_package = solver.provider.complete_package(
        DependencyPackage(package.to_dependency(), package)
    )

    assert len(complete_package.package.all_requires) == 1
    dep = complete_package.package.all_requires[0]

    assert isinstance(dep, VCSDependency)
    assert dep.constraint == demo.version
    assert (dep.name, dep.source_type, dep.source_url, dep.source_reference) == (
        dependency_git.name,
        dependency_git.source_type,
        dependency_git.source_url,
        DEFAULT_SOURCE_REF,
    )


def test_solver_duplicate_dependencies_different_constraints_merge_no_markers(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("B", "1.0"))

    package_a10 = get_package("A", "1.0")
    package_a10.add_dependency(Factory.create_dependency("C", {"version": "^1.0"}))

    package_a20 = get_package("A", "2.0")
    package_a20.add_dependency(
        Factory.create_dependency("C", {"version": "^2.0"})  # incompatible with B
    )
    package_a20.add_dependency(
        Factory.create_dependency("C", {"version": "!=2.1", "python": "3.10"})
    )

    package_b = get_package("B", "1.0")
    package_b.add_dependency(Factory.create_dependency("C", {"version": "<2.0"}))

    package_c10 = get_package("C", "1.0")
    package_c20 = get_package("C", "2.0")
    package_c21 = get_package("C", "2.1")

    repo.add_package(package_a10)
    repo.add_package(package_a20)
    repo.add_package(package_b)
    repo.add_package(package_c10)
    repo.add_package(package_c20)
    repo.add_package(package_c21)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_c10},
            {"job": "install", "package": package_a10},  # only a10, not a20
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_duplicate_dependencies_different_constraints_conflict(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.add_dependency(Factory.create_dependency("A", ">=1.1"))
    package.add_dependency(
        Factory.create_dependency("A", {"version": "<1.1", "python": "3.10"})
    )

    repo.add_package(get_package("A", "1.0"))
    repo.add_package(get_package("A", "1.1"))
    repo.add_package(get_package("A", "1.2"))

    expectation = (
        "Incompatible constraints in requirements of root (1.0):\n"
        "A (>=1.1)\n"
        'A (<1.1) ; python_version == "3.10"'
    )
    with pytest.raises(IncompatibleConstraintsError, match=re.escape(expectation)):
        solver.solve()


def test_solver_duplicate_dependencies_different_constraints_discard_no_markers1(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    """
    Initial dependencies:
        A (>=1.0)
        A (<1.2) ; python >= 3.10
        A (<1.1) ; python < 3.10

    Merged dependencies:
        A (>=1.0) ; <empty>
        A (>=1.0,<1.2) ; python >= 3.10
        A (>=1.0,<1.1) ; python < 3.10

    The dependency with an empty marker has to be ignored.
    """
    package.add_dependency(Factory.create_dependency("A", ">=1.0"))
    package.add_dependency(
        Factory.create_dependency("A", {"version": "<1.2", "python": ">=3.10"})
    )
    package.add_dependency(
        Factory.create_dependency("A", {"version": "<1.1", "python": "<3.10"})
    )
    package.add_dependency(Factory.create_dependency("B", "*"))

    package_a10 = get_package("A", "1.0")
    package_a11 = get_package("A", "1.1")
    package_a12 = get_package("A", "1.2")
    package_b = get_package("B", "1.0")
    package_b.add_dependency(Factory.create_dependency("A", "*"))

    repo.add_package(package_a10)
    repo.add_package(package_a11)
    repo.add_package(package_a12)
    repo.add_package(package_b)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            # only a10 and a11, not a12
            {"job": "install", "package": package_a10},
            {"job": "install", "package": package_a11},
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_duplicate_dependencies_different_constraints_discard_no_markers2(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    """
    Initial dependencies:
        A (>=1.0)
        A (<1.2) ; python == 3.10

    Merged dependencies:
        A (>=1.0) ; python != 3.10
        A (>=1.0,<1.2) ; python == 3.10

    The first dependency has to be ignored
    because it is not compatible with the project's python constraint.
    """
    set_package_python_versions(solver.provider, "~3.10")
    package.add_dependency(Factory.create_dependency("A", ">=1.0"))
    package.add_dependency(
        Factory.create_dependency("A", {"version": "<1.2", "python": "3.10"})
    )
    package.add_dependency(Factory.create_dependency("B", "*"))

    package_a10 = get_package("A", "1.0")
    package_a11 = get_package("A", "1.1")
    package_a12 = get_package("A", "1.2")
    package_b = get_package("B", "1.0")
    package_b.add_dependency(Factory.create_dependency("A", "*"))

    repo.add_package(package_a10)
    repo.add_package(package_a11)
    repo.add_package(package_a12)
    repo.add_package(package_b)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_a11},  # only a11, not a12
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_duplicate_dependencies_different_constraints_discard_no_markers3(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    """
    Initial dependencies:
        A (>=1.0)
        A (<1.2) ; python == 3.10

    Merged dependencies:
        A (>=1.0) ; python != 3.10
        A (>=1.0,<1.2) ; python == 3.10

    The first dependency has to be ignored
    because it is not compatible with the current environment.
    """
    package.add_dependency(Factory.create_dependency("A", ">=1.0"))
    package.add_dependency(
        Factory.create_dependency("A", {"version": "<1.2", "python": "3.10"})
    )
    package.add_dependency(Factory.create_dependency("B", "*"))

    package_a10 = get_package("A", "1.0")
    package_a11 = get_package("A", "1.1")
    package_a12 = get_package("A", "1.2")
    package_b = get_package("B", "1.0")
    package_b.add_dependency(Factory.create_dependency("A", "*"))

    repo.add_package(package_a10)
    repo.add_package(package_a11)
    repo.add_package(package_a12)
    repo.add_package(package_b)

    with solver.use_environment(MockEnv((3, 10, 0))):
        transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_a11},  # only a11, not a12
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_duplicate_dependencies_ignore_overrides_with_empty_marker_intersection(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    """
    Distinct requirements per marker:
    * Python 2.7: A (which requires B) and B
    * Python 3.6: same as Python 2.7 but with different versions
    * Python 3.7: only A
    * Python 3.8: only B
    """
    package.add_dependency(
        Factory.create_dependency("A", {"version": "1.0", "python": "~2.7"})
    )
    package.add_dependency(
        Factory.create_dependency("A", {"version": "2.0", "python": "~3.6"})
    )
    package.add_dependency(
        Factory.create_dependency("A", {"version": "3.0", "python": "~3.7"})
    )
    package.add_dependency(
        Factory.create_dependency("B", {"version": "1.0", "python": "~2.7"})
    )
    package.add_dependency(
        Factory.create_dependency("B", {"version": "2.0", "python": "~3.6"})
    )
    package.add_dependency(
        Factory.create_dependency("B", {"version": "3.0", "python": "~3.8"})
    )

    package_a10 = get_package("A", "1.0")
    package_a10.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "python": "~2.7"})
    )

    package_a20 = get_package("A", "2.0")
    package_a20.add_dependency(
        Factory.create_dependency("B", {"version": "^2.0", "python": "~3.6"})
    )

    package_a30 = get_package("A", "3.0")  # no dep to B

    package_b10 = get_package("B", "1.0")
    package_b11 = get_package("B", "1.1")
    package_b20 = get_package("B", "2.0")
    package_b21 = get_package("B", "2.1")
    package_b30 = get_package("B", "3.0")

    repo.add_package(package_a10)
    repo.add_package(package_a20)
    repo.add_package(package_a30)
    repo.add_package(package_b10)
    repo.add_package(package_b11)
    repo.add_package(package_b20)
    repo.add_package(package_b21)
    repo.add_package(package_b30)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_b10},
            {"job": "install", "package": package_b20},
            {"job": "install", "package": package_a10},
            {"job": "install", "package": package_a20},
            {"job": "install", "package": package_a30},
            {"job": "install", "package": package_b30},
        ],
    )


def test_solver_duplicate_dependencies_ignore_overrides_with_empty_marker_intersection2(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    """
    Empty intersection between top level dependency and transient dependency.
    """
    package.add_dependency(Factory.create_dependency("A", {"version": "1.0"}))
    package.add_dependency(
        Factory.create_dependency("B", {"version": ">=2.0", "python": ">=3.7"})
    )
    package.add_dependency(
        Factory.create_dependency("B", {"version": "*", "python": "<3.7"})
    )

    package_a10 = get_package("A", "1.0")
    package_a10.add_dependency(
        Factory.create_dependency("B", {"version": ">=2.0", "python": ">=3.7"})
    )
    package_a10.add_dependency(
        Factory.create_dependency("B", {"version": "*", "python": "<3.7"})
    )

    package_b10 = get_package("B", "1.0")
    package_b10.python_versions = "<3.7"
    package_b20 = get_package("B", "2.0")
    package_b20.python_versions = ">=3.7"

    repo.add_package(package_a10)
    repo.add_package(package_b10)
    repo.add_package(package_b20)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_b10},
            {"job": "install", "package": package_b20},
            {"job": "install", "package": package_a10},
        ],
    )


def test_solver_duplicate_dependencies_sub_dependencies(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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


def test_solver_duplicate_dependencies_with_overlapping_markers_simple(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.add_dependency(get_dependency("b", "1.0"))

    package_b = get_package("b", "1.0")
    dep_strings = [
        "a (>=1.0)",
        "a (>=1.1) ; python_version >= '3.7'",
        "a (<2.0) ; python_version < '3.8'",
        "a (!=1.2) ; python_version == '3.7'",
    ]
    deps = [Dependency.create_from_pep_508(dep) for dep in dep_strings]
    for dep in deps:
        package_b.add_dependency(dep)

    package_a09 = get_package("a", "0.9")
    package_a10 = get_package("a", "1.0")
    package_a11 = get_package("a", "1.1")
    package_a12 = get_package("a", "1.2")
    package_a20 = get_package("a", "2.0")

    package_a11.python_versions = ">=3.7"
    package_a12.python_versions = ">=3.7"
    package_a20.python_versions = ">=3.7"

    repo.add_package(package_a09)
    repo.add_package(package_a10)
    repo.add_package(package_a11)
    repo.add_package(package_a12)
    repo.add_package(package_a20)
    repo.add_package(package_b)

    transaction = solver.solve()
    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_a10},
            {"job": "install", "package": package_a11},
            {"job": "install", "package": package_a20},
            {"job": "install", "package": package_b},
        ],
    )
    package_b_requires = {dep.to_pep_508() for dep in ops[-1].package.requires}
    assert package_b_requires == {
        'a (>=1.0,<2.0) ; python_version < "3.7"',
        'a (>=1.1,!=1.2,<2.0) ; python_version == "3.7"',
        'a (>=1.1) ; python_version >= "3.8"',
    }


def test_solver_duplicate_dependencies_with_overlapping_markers_complex(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    """
    Dependencies with overlapping markers from
    https://pypi.org/project/opencv-python/4.6.0.66/
    """
    package.add_dependency(get_dependency("opencv", "4.6.0.66"))

    opencv_package = get_package("opencv", "4.6.0.66")
    dep_strings = [
        "numpy (>=1.13.3) ; python_version < '3.7'",
        "numpy (>=1.21.2) ; python_version >= '3.10'",
        (
            "numpy (>=1.21.2) ; python_version >= '3.6' "
            "and platform_system == 'Darwin' and platform_machine == 'arm64'"
        ),
        (
            "numpy (>=1.19.3) ; python_version >= '3.6' "
            "and platform_system == 'Linux' and platform_machine == 'aarch64'"
        ),
        "numpy (>=1.14.5) ; python_version >= '3.7'",
        "numpy (>=1.17.3) ; python_version >= '3.8'",
        "numpy (>=1.19.3) ; python_version >= '3.9'",
    ]
    deps = [Dependency.create_from_pep_508(dep) for dep in dep_strings]
    for dep in deps:
        opencv_package.add_dependency(dep)

    for version in {"1.13.3", "1.21.2", "1.19.3", "1.14.5", "1.17.3"}:
        repo.add_package(get_package("numpy", version))
    repo.add_package(opencv_package)

    transaction = solver.solve()
    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": get_package("numpy", "1.21.2")},
            {"job": "install", "package": opencv_package},
        ],
    )
    opencv_requires = {dep.to_pep_508() for dep in ops[-1].package.requires}
    expectation = (
        {  # concise solution, but too expensive
            (
                "numpy (>=1.21.2) ;"
                ' platform_system == "Darwin" and platform_machine == "arm64"'
                ' and python_version >= "3.6" or python_version >= "3.10"'
            ),
            (
                'numpy (>=1.19.3) ; python_version >= "3.9" and python_version < "3.10"'
                ' and platform_system != "Darwin" or platform_system == "Linux"'
                ' and platform_machine == "aarch64" and python_version < "3.10"'
                ' and python_version >= "3.6" or python_version >= "3.9"'
                ' and python_version < "3.10" and platform_machine != "arm64"'
            ),
            (
                'numpy (>=1.17.3) ; python_version >= "3.8" and python_version < "3.9"'
                ' and (platform_system != "Darwin" or platform_machine != "arm64")'
                ' and (platform_system != "Linux" or platform_machine != "aarch64")'
            ),
            (
                'numpy (>=1.14.5) ; python_version >= "3.7" and python_version < "3.8"'
                ' and (platform_system != "Darwin" or platform_machine != "arm64")'
                ' and (platform_system != "Linux" or platform_machine != "aarch64")'
            ),
            (
                'numpy (>=1.13.3) ; python_version < "3.7"'
                ' and (python_version < "3.6" or platform_system != "Darwin"'
                ' or platform_machine != "arm64") and (python_version < "3.6"'
                ' or platform_system != "Linux" or platform_machine != "aarch64")'
            ),
        },
        {  # current solution
            (
                "numpy (>=1.21.2) ;"
                ' python_version >= "3.6" and platform_system == "Darwin"'
                ' and platform_machine == "arm64" or python_version >= "3.10"'
            ),
            (
                'numpy (>=1.19.3) ; python_version >= "3.9" and python_version < "3.10"'
                ' and platform_system != "Darwin" or python_version >= "3.9"'
                ' and python_version < "3.10" and platform_machine != "arm64"'
                ' or platform_system == "Linux" and python_version < "3.10"'
                ' and platform_machine == "aarch64" and python_version >= "3.6"'
            ),
            (
                'numpy (>=1.17.3) ; python_version < "3.9"'
                ' and (platform_system != "Darwin" and platform_system != "Linux")'
                ' and python_version >= "3.8" or python_version < "3.9"'
                ' and platform_system != "Darwin" and python_version >= "3.8"'
                ' and platform_machine != "aarch64" or python_version < "3.9"'
                ' and platform_machine != "arm64" and python_version >= "3.8"'
                ' and platform_system != "Linux" or python_version < "3.9"'
                ' and (platform_machine != "arm64" and platform_machine != "aarch64")'
                ' and python_version >= "3.8"'
            ),
            (
                'numpy (>=1.14.5) ; python_version < "3.8"'
                ' and (platform_system != "Darwin" and platform_system != "Linux")'
                ' and python_version >= "3.7" or python_version < "3.8"'
                ' and platform_system != "Darwin" and python_version >= "3.7"'
                ' and platform_machine != "aarch64" or python_version < "3.8"'
                ' and platform_machine != "arm64" and python_version >= "3.7"'
                ' and platform_system != "Linux" or python_version < "3.8"'
                ' and (platform_machine != "arm64" and platform_machine != "aarch64")'
                ' and python_version >= "3.7"'
            ),
            (
                'numpy (>=1.13.3) ; python_version < "3.6" or python_version < "3.7"'
                ' and (platform_system != "Darwin" and platform_system != "Linux")'
                ' or python_version < "3.7" and platform_system != "Darwin"'
                ' and platform_machine != "aarch64" or python_version < "3.7"'
                ' and platform_machine != "arm64" and platform_system != "Linux"'
                ' or python_version < "3.7" and (platform_machine != "arm64"'
                ' and platform_machine != "aarch64")'
            ),
        },
    )
    assert opencv_requires in expectation


def test_duplicate_path_dependencies(
    solver: Solver, package: ProjectPackage, fixture_dir: FixtureDirGetter
) -> None:
    set_package_python_versions(solver.provider, "^3.7")
    project_dir = fixture_dir("with_conditional_path_deps")

    path1 = (project_dir / "demo_one").as_posix()
    demo1 = Package("demo", "1.2.3", source_type="directory", source_url=path1)
    package.add_dependency(
        Factory.create_dependency(
            "demo", {"path": path1, "markers": "sys_platform == 'linux'"}
        )
    )

    path2 = (project_dir / "demo_two").as_posix()
    demo2 = Package("demo", "1.2.3", source_type="directory", source_url=path2)
    package.add_dependency(
        Factory.create_dependency(
            "demo", {"path": path2, "markers": "sys_platform == 'win32'"}
        )
    )

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": demo1},
            {"job": "install", "package": demo2},
        ],
    )


def test_duplicate_path_dependencies_same_path(
    solver: Solver, package: ProjectPackage, fixture_dir: FixtureDirGetter
) -> None:
    set_package_python_versions(solver.provider, "^3.7")
    project_dir = fixture_dir("with_conditional_path_deps")

    path1 = (project_dir / "demo_one").as_posix()
    demo1 = Package("demo", "1.2.3", source_type="directory", source_url=path1)
    package.add_dependency(
        Factory.create_dependency(
            "demo", {"path": path1, "markers": "sys_platform == 'linux'"}
        )
    )
    package.add_dependency(
        Factory.create_dependency(
            "demo", {"path": path1, "markers": "sys_platform == 'win32'"}
        )
    )

    transaction = solver.solve()

    check_solver_result(transaction, [{"job": "install", "package": demo1}])


def test_solver_fails_if_dependency_name_does_not_match_package(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.add_dependency(
        Factory.create_dependency(
            "my-demo", {"git": "https://github.com/demo/demo.git"}
        )
    )

    with pytest.raises(RuntimeError):
        solver.solve()


def test_solver_does_not_get_stuck_in_recursion_on_circular_dependency(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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


def test_solver_can_resolve_git_dependencies(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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
        source_reference=DEFAULT_SOURCE_REF,
        source_resolved_reference=MOCK_DEFAULT_GIT_REVISION,
    )

    ops = check_solver_result(
        transaction,
        [{"job": "install", "package": pendulum}, {"job": "install", "package": demo}],
    )

    op = ops[1]

    assert op.package.source_type == "git"
    assert op.package.source_reference == DEFAULT_SOURCE_REF
    assert op.package.source_resolved_reference is not None
    assert op.package.source_resolved_reference.startswith("9cf87a2")


def test_solver_can_resolve_git_dependencies_with_extras(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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
        source_reference=DEFAULT_SOURCE_REF,
        source_resolved_reference=MOCK_DEFAULT_GIT_REVISION,
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
def test_solver_can_resolve_git_dependencies_with_ref(
    solver: Solver, repo: Repository, package: ProjectPackage, ref: dict[str, str]
) -> None:
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    demo = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference=ref[next(iter(ref.keys()))],
        source_resolved_reference=MOCK_DEFAULT_GIT_REVISION,
    )

    assert demo.source_type is not None
    assert demo.source_url is not None
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
    assert op.package.source_reference == ref[next(iter(ref.keys()))]
    assert op.package.source_resolved_reference is not None
    assert op.package.source_resolved_reference.startswith("9cf87a2")


def test_solver_does_not_trigger_conflict_for_python_constraint_if_python_requirement_is_compatible(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "~2.7 || ^3.4")
    package.add_dependency(
        Factory.create_dependency("A", {"version": "^1.0", "python": "^3.6"})
    )

    package_a = get_package("A", "1.0.0")
    package_a.python_versions = ">=3.6"

    repo.add_package(package_a)

    transaction = solver.solve()

    check_solver_result(transaction, [{"job": "install", "package": package_a}])


def test_solver_does_not_trigger_conflict_for_python_constraint_if_python_requirement_is_compatible_multiple(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "~2.7 || ^3.4")
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
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "~2.7 || ^3.4")
    package.add_dependency(
        Factory.create_dependency("A", {"version": "^1.0", "python": "^3.5"})
    )

    package_a = get_package("A", "1.0.0")
    package_a.python_versions = ">=3.6"

    repo.add_package(package_a)

    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_finds_compatible_package_for_dependency_python_not_fully_compatible_with_package_python(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "~2.7 || ^3.4")
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
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    dep1 = Dependency.create_from_pep_508('B (>=1.0); extra == "foo"')
    dep1.activate()
    dep2 = Dependency.create_from_pep_508('B (>=2.0); extra == "bar"')
    dep2.activate()

    package.add_dependency(
        Factory.create_dependency("A", {"version": "^1.0", "extras": ["foo", "bar"]})
    )

    package_a = get_package("A", "1.0.0")
    package_a.extras = {
        canonicalize_name("foo"): [dep1],
        canonicalize_name("bar"): [dep2],
    }
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
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "~2.7 || ^3.4")
    dependency_a = Factory.create_dependency("A", {"version": "^1.0", "python": "^3.6"})
    package.add_dependency(dependency_a)
    package.add_dependency(Factory.create_dependency("B", "^1.0"))

    package_a = get_package("A", "1.0.0")
    package_a.python_versions = ">=3.6"
    package_a.marker = parse_marker(
        'python_version >= "3.6" and python_version < "4.0"'
    )

    package_b = get_package("B", "1.0.0")

    repo.add_package(package_a)
    repo.add_package(package_b)

    dep_package_a = DependencyPackage(dependency_a, package_a)
    solver.provider._locked = {canonicalize_name("A"): [dep_package_a]}
    transaction = solver.solve(use_latest=[package_b.name])

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_a},
            {"job": "install", "package": package_b},
        ],
    )


def test_solver_returns_extras_if_requested_in_dependencies_and_not_in_root_package(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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
    package_c.extras = {
        canonicalize_name("foo"): [Factory.create_dependency("D", "^1.0")]
    }

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
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "^3.6")
    package.add_dependency(Factory.create_dependency("A", "^1.0"))
    package.add_dependency(Factory.create_dependency("B", "^2.0"))

    package_a = get_package("A", "1.0.0")
    package_a.add_dependency(
        Dependency.create_from_pep_508(
            'B (<2.0); platform_python_implementation == "PyPy" and python_full_version'
            ' < "2.7.9"'
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


def test_solver_git_dependencies_update(
    package: ProjectPackage, repo: Repository, pool: RepositoryPool, io: NullIO
) -> None:
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    demo_installed = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference=DEFAULT_SOURCE_REF,
        source_resolved_reference="123456",
    )
    demo = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference=DEFAULT_SOURCE_REF,
        source_resolved_reference=MOCK_DEFAULT_GIT_REVISION,
    )

    package.add_dependency(
        Factory.create_dependency("demo", {"git": "https://github.com/demo/demo.git"})
    )

    solver = Solver(package, pool, [demo_installed], [], io)
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
    assert isinstance(op, Update)
    assert op.package.source_type == "git"
    assert op.package.source_reference == DEFAULT_SOURCE_REF
    assert op.package.source_resolved_reference is not None
    assert op.package.source_resolved_reference.startswith("9cf87a2")
    assert op.initial_package.source_resolved_reference == "123456"


def test_solver_git_dependencies_update_skipped(
    package: ProjectPackage, repo: Repository, pool: RepositoryPool, io: NullIO
) -> None:
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
        source_resolved_reference=MOCK_DEFAULT_GIT_REVISION,
    )

    package.add_dependency(
        Factory.create_dependency("demo", {"git": "https://github.com/demo/demo.git"})
    )

    solver = Solver(package, pool, [demo], [], io)
    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": pendulum},
            {"job": "install", "package": demo, "skipped": True},
        ],
    )


def test_solver_git_dependencies_short_hash_update_skipped(
    package: ProjectPackage, repo: Repository, pool: RepositoryPool, io: NullIO
) -> None:
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    demo = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference=MOCK_DEFAULT_GIT_REVISION,
        source_resolved_reference=MOCK_DEFAULT_GIT_REVISION,
    )

    package.add_dependency(
        Factory.create_dependency(
            "demo", {"git": "https://github.com/demo/demo.git", "rev": "9cf87a2"}
        )
    )

    solver = Solver(package, pool, [demo], [], io)
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
                    source_reference=MOCK_DEFAULT_GIT_REVISION,
                    source_resolved_reference=MOCK_DEFAULT_GIT_REVISION,
                ),
                "skipped": True,
            },
        ],
    )


def test_solver_can_resolve_directory_dependencies(
    solver: Solver,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: FixtureDirGetter,
) -> None:
    pendulum = get_package("pendulum", "2.0.3")
    repo.add_package(pendulum)

    path = (fixture_dir("git") / "github.com" / "demo" / "demo").as_posix()

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
    repo: Repository,
    pool: RepositoryPool,
    io: NullIO,
    fixture_dir: FixtureDirGetter,
) -> None:
    base = fixture_dir("project_with_nested_local")
    poetry = Factory().create_poetry(cwd=base)
    package = poetry.package

    solver = Solver(package, pool, [], [], io)

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


def test_solver_can_resolve_directory_dependencies_with_extras(
    solver: Solver,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: FixtureDirGetter,
) -> None:
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    path = (fixture_dir("git") / "github.com" / "demo" / "demo").as_posix()

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


def test_solver_can_resolve_sdist_dependencies(
    solver: Solver,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: FixtureDirGetter,
) -> None:
    pendulum = get_package("pendulum", "2.0.3")
    repo.add_package(pendulum)

    path = (fixture_dir("distributions") / "demo-0.1.0.tar.gz").as_posix()

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


def test_solver_can_resolve_sdist_dependencies_with_extras(
    solver: Solver,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: FixtureDirGetter,
) -> None:
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    path = (fixture_dir("distributions") / "demo-0.1.0.tar.gz").as_posix()

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


def test_solver_can_resolve_wheel_dependencies(
    solver: Solver,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: FixtureDirGetter,
) -> None:
    pendulum = get_package("pendulum", "2.0.3")
    repo.add_package(pendulum)

    path = (fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl").as_posix()

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


def test_solver_can_resolve_wheel_dependencies_with_extras(
    solver: Solver,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: FixtureDirGetter,
) -> None:
    pendulum = get_package("pendulum", "2.0.3")
    cleo = get_package("cleo", "1.0.0")
    repo.add_package(pendulum)
    repo.add_package(cleo)

    path = (fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl").as_posix()

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
    package: ProjectPackage, io: NullIO
) -> None:
    repo = MockLegacyRepository()
    pool = RepositoryPool([repo])

    solver = Solver(package, pool, [], [], io)

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
    package: ProjectPackage,
    io: NullIO,
) -> None:
    package.python_versions = "^3.7"

    repo = MockLegacyRepository()
    pool = RepositoryPool([repo])

    solver = Solver(package, pool, [], [], io)

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


def test_solver_skips_invalid_versions(package: ProjectPackage, io: NullIO) -> None:
    package.python_versions = "^3.7"

    repo = MockPyPIRepository()
    pool = RepositoryPool([repo])

    solver = Solver(package, pool, [], [], io)

    package.add_dependency(Factory.create_dependency("trackpy", "^0.4"))

    transaction = solver.solve()

    check_solver_result(
        transaction, [{"job": "install", "package": get_package("trackpy", "0.4.1")}]
    )


def test_multiple_constraints_on_root(
    package: ProjectPackage, solver: Solver, repo: Repository
) -> None:
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
    package: ProjectPackage, io: NullIO
) -> None:
    package.python_versions = "^3.7"
    package.add_dependency(Factory.create_dependency("tomlkit", {"version": "^0.5"}))

    repo = MockLegacyRepository()
    pool = RepositoryPool([repo, MockPyPIRepository()])

    solver = Solver(package, pool, [], [], io)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction, [{"job": "install", "package": get_package("tomlkit", "0.5.3")}]
    )

    assert ops[0].package.source_type is None
    assert ops[0].package.source_url is None


def test_solver_chooses_from_correct_repository_if_forced(
    package: ProjectPackage, io: NullIO
) -> None:
    package.python_versions = "^3.7"
    package.add_dependency(
        Factory.create_dependency("tomlkit", {"version": "^0.5", "source": "legacy"})
    )

    repo = MockLegacyRepository()
    pool = RepositoryPool([repo, MockPyPIRepository()])

    solver = Solver(package, pool, [], [], io)

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

    assert ops[0].package.source_url == "http://legacy.foo.bar"


def test_solver_chooses_from_correct_repository_if_forced_and_transitive_dependency(
    package: ProjectPackage,
    io: NullIO,
) -> None:
    package.python_versions = "^3.7"
    package.add_dependency(Factory.create_dependency("foo", "^1.0"))
    package.add_dependency(
        Factory.create_dependency("tomlkit", {"version": "^0.5", "source": "legacy"})
    )

    repo = Repository("repo")
    foo = get_package("foo", "1.0.0")
    foo.add_dependency(Factory.create_dependency("tomlkit", "^0.5.0"))
    repo.add_package(foo)
    pool = RepositoryPool([MockLegacyRepository(), repo, MockPyPIRepository()])

    solver = Solver(package, pool, [], [], io)

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

    assert ops[0].package.source_url == "http://legacy.foo.bar"

    assert ops[1].package.source_type is None
    assert ops[1].package.source_url is None


def test_solver_does_not_choose_from_secondary_repository_by_default(
    package: ProjectPackage, io: NullIO
) -> None:
    package.python_versions = "^3.7"
    package.add_dependency(Factory.create_dependency("clikit", {"version": "^0.2.0"}))

    pool = RepositoryPool()
    pool.add_repository(MockPyPIRepository(), priority=Priority.SECONDARY)
    pool.add_repository(MockLegacyRepository())

    solver = Solver(package, pool, [], [], io)

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

    assert ops[0].package.source_url == "http://legacy.foo.bar"
    assert ops[1].package.source_type is None
    assert ops[1].package.source_url is None
    assert ops[2].package.source_url == "http://legacy.foo.bar"


def test_solver_chooses_from_secondary_if_explicit(
    package: ProjectPackage,
    io: NullIO,
) -> None:
    package.python_versions = "^3.7"
    package.add_dependency(
        Factory.create_dependency("clikit", {"version": "^0.2.0", "source": "PyPI"})
    )

    pool = RepositoryPool()
    pool.add_repository(MockPyPIRepository(), priority=Priority.SECONDARY)
    pool.add_repository(MockLegacyRepository())

    solver = Solver(package, pool, [], [], io)

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

    assert ops[0].package.source_url == "http://legacy.foo.bar"
    assert ops[1].package.source_type is None
    assert ops[1].package.source_url is None
    assert ops[2].package.source_type is None
    assert ops[2].package.source_url is None


def test_solver_does_not_choose_from_explicit_repository(
    package: ProjectPackage, io: NullIO
) -> None:
    package.python_versions = "^3.7"
    package.add_dependency(Factory.create_dependency("attrs", {"version": "^17.4.0"}))

    pool = RepositoryPool()
    pool.add_repository(MockPyPIRepository(), priority=Priority.EXPLICIT)
    pool.add_repository(MockLegacyRepository())

    solver = Solver(package, pool, [], [], io)

    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_chooses_direct_dependency_from_explicit_if_explicit(
    package: ProjectPackage,
    io: NullIO,
) -> None:
    package.python_versions = "^3.7"
    package.add_dependency(
        Factory.create_dependency("pylev", {"version": "^1.2.0", "source": "PyPI"})
    )

    pool = RepositoryPool()
    pool.add_repository(MockPyPIRepository(), priority=Priority.EXPLICIT)
    pool.add_repository(MockLegacyRepository())

    solver = Solver(package, pool, [], [], io)

    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": get_package("pylev", "1.3.0")},
        ],
    )

    assert ops[0].package.source_type is None
    assert ops[0].package.source_url is None


def test_solver_ignores_explicit_repo_for_transient_dependencies(
    package: ProjectPackage,
    io: NullIO,
) -> None:
    # clikit depends on pylev, which is in MockPyPIRepository (explicit) but not in
    # MockLegacyRepository
    package.python_versions = "^3.7"
    package.add_dependency(
        Factory.create_dependency("clikit", {"version": "^0.2.0", "source": "PyPI"})
    )

    pool = RepositoryPool()
    pool.add_repository(MockPyPIRepository(), priority=Priority.EXPLICIT)
    pool.add_repository(MockLegacyRepository())

    solver = Solver(package, pool, [], [], io)

    with pytest.raises(SolverProblemError):
        solver.solve()


@pytest.mark.parametrize(
    ("lib_versions", "other_versions"),
    [
        # number of versions influences which dependency is resolved first
        (["1.0", "2.0"], ["1.0", "1.1", "2.0"]),  # more other than lib
        (["1.0", "1.1", "2.0"], ["1.0", "2.0"]),  # more lib than other
    ],
)
def test_direct_dependency_with_extras_from_explicit_and_transitive_dependency(
    package: ProjectPackage,
    repo: Repository,
    pool: RepositoryPool,
    io: NullIO,
    lib_versions: list[str],
    other_versions: list[str],
) -> None:
    """
    The root package depends on "lib[extra]" and "other", both with an explicit source.
    "other" depends on "lib" (without an extra and of course without an explicit source
    because explicit sources can only be defined in the root package).

    If "other" is resolved before "lib[extra]", the solver must not try to fetch "lib"
    from the default source but from the explicit source defined for "lib[extra]".
    """
    package.add_dependency(
        Factory.create_dependency(
            "lib", {"version": ">=1.0", "extras": ["extra"], "source": "explicit"}
        )
    )
    package.add_dependency(
        Factory.create_dependency("other", {"version": ">=1.0", "source": "explicit"})
    )

    explicit_repo = Repository("explicit")
    pool.add_repository(explicit_repo, priority=Priority.EXPLICIT)

    package_extra = get_package("extra", "1.0")
    repo.add_package(package_extra)  # extra only in default repo

    for version in lib_versions:
        package_lib = get_package("lib", version)

        dep_extra = get_dependency("extra", ">=1.0")
        package_lib.add_dependency(
            Factory.create_dependency("extra", {"version": ">=1.0", "optional": True})
        )
        package_lib.extras = {canonicalize_name("extra"): [dep_extra]}

        explicit_repo.add_package(package_lib)  # lib only in explicit repo

    for version in other_versions:
        package_other = get_package("other", version)
        package_other.add_dependency(Factory.create_dependency("lib", ">=1.0"))
        explicit_repo.add_package(package_other)  # other only in explicit repo

    solver = Solver(package, pool, [], [], io)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": get_package("extra", "1.0")},
            {"job": "install", "package": get_package("lib", "2.0")},
            {"job": "install", "package": get_package("other", "2.0")},
        ],
    )


@pytest.mark.parametrize(
    ("lib_versions", "other_versions"),
    [
        # number of versions influences which dependency is resolved first
        (["1.0", "2.0"], ["1.0", "1.1", "2.0"]),  # more other than lib
        (["1.0", "1.1", "2.0"], ["1.0", "2.0"]),  # more lib than other
    ],
)
def test_direct_dependency_with_extras_from_explicit_and_transitive_dependency2(
    package: ProjectPackage,
    repo: Repository,
    pool: RepositoryPool,
    io: NullIO,
    lib_versions: list[str],
    other_versions: list[str],
) -> None:
    """
    The root package depends on "lib[extra]" and "other", both with an explicit source.
    "other" depends on "lib[other-extra]" (with another extra and of course without an
    explicit source because explicit sources can only be defined in the root package).

    The solver must not try to fetch "lib[other-extra]" from the default source
    but from the explicit source defined for "lib[extra]".
    """
    package.add_dependency(
        Factory.create_dependency(
            "lib", {"version": ">=1.0", "extras": ["extra"], "source": "explicit"}
        )
    )
    package.add_dependency(
        Factory.create_dependency("other", {"version": ">=1.0", "source": "explicit"})
    )

    explicit_repo = Repository("explicit")
    pool.add_repository(explicit_repo, priority=Priority.EXPLICIT)

    package_extra = get_package("extra", "1.0")
    repo.add_package(package_extra)  # extra only in default repo
    package_other_extra = get_package("other-extra", "1.0")
    repo.add_package(package_other_extra)  # extra only in default repo

    for version in lib_versions:
        package_lib = get_package("lib", version)

        dep_extra = get_dependency("extra", ">=1.0")
        package_lib.add_dependency(
            Factory.create_dependency("extra", {"version": ">=1.0", "optional": True})
        )

        dep_other_extra = get_dependency("other-extra", ">=1.0")
        package_lib.add_dependency(
            Factory.create_dependency(
                "other-extra", {"version": ">=1.0", "optional": True}
            )
        )
        package_lib.extras = {
            canonicalize_name("extra"): [dep_extra],
            canonicalize_name("other-extra"): [dep_other_extra],
        }

        explicit_repo.add_package(package_lib)  # lib only in explicit repo

    for version in other_versions:
        package_other = get_package("other", version)
        package_other.add_dependency(
            Factory.create_dependency(
                "lib", {"version": ">=1.0", "extras": ["other-extra"]}
            )
        )
        explicit_repo.add_package(package_other)  # other only in explicit repo

    solver = Solver(package, pool, [], [], io)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": get_package("other-extra", "1.0")},
            {"job": "install", "package": get_package("extra", "1.0")},
            {"job": "install", "package": get_package("lib", "2.0")},
            {"job": "install", "package": get_package("other", "2.0")},
        ],
    )


@pytest.mark.parametrize("locked", [False, True])
def test_multiple_constraints_explicit_source_transitive_locked_use_latest(
    package: ProjectPackage,
    repo: Repository,
    pool: RepositoryPool,
    io: NullIO,
    locked: bool,
) -> None:
    """
    The root package depends on
     * lib[extra] == 1.0; sys_platform != "linux" with source=explicit1
     * lib[extra] == 2.0; sys_platform == "linux" with source=explicit2
     * other >= 1.0
    "other" depends on "lib" (without an extra and of course without an explicit source
    because explicit sources can only be defined in the root package).

    If only "other" is in use_latest (equivalent to "poetry update other"),
    the transitive dependency of "other" on "lib" is resolved before
    the direct dependency on "lib[extra]" (if packages have been locked before).
    We still have to make sure that the locked package is looked up in the explicit
    source although the DependencyCache is not used for locked packages,
    so we can't rely on it to propagate the correct source.
    """
    package.add_dependency(
        Factory.create_dependency(
            "lib",
            {
                "version": "1.0",
                "extras": ["extra"],
                "source": "explicit1",
                "markers": "sys_platform != 'linux'",
            },
        )
    )
    package.add_dependency(
        Factory.create_dependency(
            "lib",
            {
                "version": "2.0",
                "extras": ["extra"],
                "source": "explicit2",
                "markers": "sys_platform == 'linux'",
            },
        )
    )
    package.add_dependency(Factory.create_dependency("other", {"version": ">=1.0"}))

    explicit_repo1 = Repository("explicit1")
    pool.add_repository(explicit_repo1, priority=Priority.EXPLICIT)
    explicit_repo2 = Repository("explicit2")
    pool.add_repository(explicit_repo2, priority=Priority.EXPLICIT)

    dep_extra = get_dependency("extra", ">=1.0")
    dep_extra_opt = Factory.create_dependency(
        "extra", {"version": ">=1.0", "optional": True}
    )
    package_lib1 = Package(
        "lib", "1.0", source_type="legacy", source_reference="explicit1"
    )
    package_lib1.extras = {canonicalize_name("extra"): [dep_extra]}
    package_lib1.add_dependency(dep_extra_opt)
    explicit_repo1.add_package(package_lib1)
    package_lib2 = Package(
        "lib", "2.0", source_type="legacy", source_reference="explicit2"
    )
    package_lib2.extras = {canonicalize_name("extra"): [dep_extra]}
    package_lib2.add_dependency(dep_extra_opt)
    explicit_repo2.add_package(package_lib2)

    package_extra = Package("extra", "1.0")
    repo.add_package(package_extra)
    package_other = Package("other", "1.5")
    package_other.add_dependency(Factory.create_dependency("lib", ">=1.0"))
    repo.add_package(package_other)

    if locked:
        locked_packages = [package_extra, package_lib1, package_lib2, package_other]
        use_latest = [canonicalize_name("other")]
    else:
        locked_packages = []
        use_latest = None
    solver = Solver(package, pool, [], locked_packages, io)

    transaction = solver.solve(use_latest=use_latest)

    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_extra},
            {"job": "install", "package": package_lib1},
            {"job": "install", "package": package_lib2},
            {"job": "install", "package": package_other},
        ],
    )
    assert ops[1].package.source_reference == "explicit1"
    assert ops[2].package.source_reference == "explicit2"


def test_solver_discards_packages_with_empty_markers(
    package: ProjectPackage,
    repo: Repository,
    pool: RepositoryPool,
    io: NullIO,
) -> None:
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

    solver = Solver(package, pool, [], [], io)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_c},
            {"job": "install", "package": package_a},
        ],
    )


def test_solver_does_not_raise_conflict_for_conditional_dev_dependencies(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "~2.7 || ^3.5")
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
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "~2.7 || ^3.5")
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
    requests.extras = {
        canonicalize_name("security"): [get_dependency("idna", ">=2.0.0")]
    }
    idna = get_package("idna", "2.8")

    repo.add_package(requests)
    repo.add_package(idna)

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [{"job": "install", "package": idna}, {"job": "install", "package": requests}],
    )


def test_solver_does_not_fail_with_locked_git_and_non_git_dependencies(
    package: ProjectPackage,
    repo: Repository,
    pool: RepositoryPool,
    io: NullIO,
) -> None:
    package.add_dependency(
        Factory.create_dependency("demo", {"git": "https://github.com/demo/demo.git"})
    )
    package.add_dependency(Factory.create_dependency("a", "^1.2.3"))

    git_package = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference=DEFAULT_SOURCE_REF,
        source_resolved_reference=MOCK_DEFAULT_GIT_REVISION,
    )

    repo.add_package(get_package("a", "1.2.3"))
    repo.add_package(Package("pendulum", "2.1.2"))

    installed = [git_package]
    locked = [get_package("a", "1.2.3"), git_package]

    solver = Solver(package, pool, installed, locked, io)
    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": get_package("a", "1.2.3")},
            {"job": "install", "package": git_package, "skipped": True},
        ],
    )


def test_ignore_python_constraint_no_overlap_dependencies(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "~2.7 || ^3.5")
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


def test_solver_synchronize_single(
    package: ProjectPackage, pool: RepositoryPool, io: NullIO
) -> None:
    package_a = get_package("a", "1.0")

    solver = Solver(package, pool, [package_a], [], io)
    transaction = solver.solve()

    check_solver_result(
        transaction, [{"job": "remove", "package": package_a}], synchronize=True
    )


@pytest.mark.skip(reason="Poetry no longer has critical package requirements")
def test_solver_with_synchronization_keeps_critical_package(
    package: ProjectPackage,
    pool: RepositoryPool,
    io: NullIO,
) -> None:
    package_pip = get_package("setuptools", "1.0")

    solver = Solver(package, pool, [package_pip], [], io)
    transaction = solver.solve()

    check_solver_result(transaction, [])


def test_solver_cannot_choose_another_version_for_directory_dependencies(
    solver: Solver,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: FixtureDirGetter,
) -> None:
    pendulum = get_package("pendulum", "2.0.3")
    demo = get_package("demo", "0.1.0")
    foo = get_package("foo", "1.2.3")
    foo.add_dependency(Factory.create_dependency("demo", "<0.1.2"))
    repo.add_package(foo)
    repo.add_package(demo)
    repo.add_package(pendulum)

    path = (fixture_dir("git") / "github.com" / "demo" / "demo").as_posix()

    package.add_dependency(Factory.create_dependency("demo", {"path": path}))
    package.add_dependency(Factory.create_dependency("foo", "^1.2.3"))

    # This is not solvable since the demo version is pinned
    # via the directory dependency
    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_cannot_choose_another_version_for_file_dependencies(
    solver: Solver,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: FixtureDirGetter,
) -> None:
    pendulum = get_package("pendulum", "2.0.3")
    demo = get_package("demo", "0.0.8")
    foo = get_package("foo", "1.2.3")
    foo.add_dependency(Factory.create_dependency("demo", "<0.1.0"))
    repo.add_package(foo)
    repo.add_package(demo)
    repo.add_package(pendulum)

    path = (fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl").as_posix()

    package.add_dependency(Factory.create_dependency("demo", {"path": path}))
    package.add_dependency(Factory.create_dependency("foo", "^1.2.3"))

    # This is not solvable since the demo version is pinned
    # via the file dependency
    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_cannot_choose_another_version_for_git_dependencies(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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
    solver: Solver,
    repo: Repository,
    package: ProjectPackage,
    http: type[httpretty.httpretty],
    fixture_dir: FixtureDirGetter,
) -> None:
    path = fixture_dir("distributions") / "demo-0.1.0-py2.py3-none-any.whl"

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


@pytest.mark.parametrize("explicit_source", [True, False])
def test_solver_cannot_choose_url_dependency_for_explicit_source(
    solver: Solver,
    repo: Repository,
    package: ProjectPackage,
    explicit_source: bool,
) -> None:
    """A direct origin dependency cannot satisfy a version dependency with an explicit
    source. (It can satisfy a version dependency without an explicit source.)
    """
    package.add_dependency(
        Factory.create_dependency(
            "demo",
            {
                "markers": "sys_platform != 'darwin'",
                "url": "https://foo.bar/distributions/demo-0.1.0-py2.py3-none-any.whl",
            },
        )
    )
    package.add_dependency(
        Factory.create_dependency(
            "demo",
            {
                "version": "0.1.0",
                "markers": "sys_platform == 'darwin'",
                "source": "repo" if explicit_source else None,
            },
        )
    )

    package_pendulum = get_package("pendulum", "1.4.4")
    package_demo = get_package("demo", "0.1.0")
    package_demo_url = Package(
        "demo",
        "0.1.0",
        source_type="url",
        source_url="https://foo.bar/distributions/demo-0.1.0-py2.py3-none-any.whl",
    )
    # The url demo dependency depends on pendulum.
    repo.add_package(package_pendulum)
    repo.add_package(package_demo)

    transaction = solver.solve()

    if explicit_source:
        # direct origin cannot satisfy explicit source
        # -> package_demo MUST be included
        expected = [
            {"job": "install", "package": package_pendulum},
            {"job": "install", "package": package_demo_url},
            {"job": "install", "package": package_demo},
        ]
    else:
        # direct origin can satisfy dependency without source
        # -> package_demo NEED NOT (but could) be included
        expected = [
            {"job": "install", "package": package_pendulum},
            {"job": "install", "package": package_demo_url},
        ]

    check_solver_result(transaction, expected)


def test_solver_should_not_update_same_version_packages_if_installed_has_no_source_type(
    package: ProjectPackage, repo: Repository, pool: RepositoryPool, io: NullIO
) -> None:
    package.add_dependency(Factory.create_dependency("foo", "1.0.0"))

    foo = Package(
        "foo",
        "1.0.0",
        source_type="legacy",
        source_url="https://foo.bar",
        source_reference="custom",
    )
    repo.add_package(foo)

    solver = Solver(package, pool, [get_package("foo", "1.0.0")], [], io)
    transaction = solver.solve()

    check_solver_result(
        transaction, [{"job": "install", "package": foo, "skipped": True}]
    )


def test_solver_should_use_the_python_constraint_from_the_environment_if_available(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    set_package_python_versions(solver.provider, "~2.7 || ^3.5")
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
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.python_versions = "^3.6"
    set_package_python_versions(solver.provider, "^3.6")
    package.add_dependency(
        Factory.create_dependency("dataclasses", {"version": "^0.7", "python": "<3.7"})
    )

    dataclasses = get_package("dataclasses", "0.7")
    dataclasses.python_versions = ">=3.6, <3.7"

    repo.add_package(dataclasses)
    transaction = solver.solve()

    check_solver_result(transaction, [{"job": "install", "package": dataclasses}])


def test_solver_can_resolve_transitive_extras(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.add_dependency(Factory.create_dependency("requests", "^2.24.0"))
    package.add_dependency(Factory.create_dependency("PyOTA", "^2.1.0"))

    requests = get_package("requests", "2.24.0")
    requests.add_dependency(Factory.create_dependency("certifi", ">=2017.4.17"))
    dep = get_dependency("PyOpenSSL", ">=0.14")
    requests.add_dependency(
        Factory.create_dependency("PyOpenSSL", {"version": ">=0.14", "optional": True})
    )
    requests.extras = {canonicalize_name("security"): [dep]}
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


def test_solver_can_resolve_for_packages_with_missing_extras(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
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
    django_anymail.extras = {
        canonicalize_name("amazon_ses"): [Factory.create_dependency("boto3", "*")]
    }
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
    package: ProjectPackage, repo: Repository, pool: RepositoryPool, io: NullIO
) -> None:
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

    repo.add_package(futures)
    repo.add_package(pre_commit)

    solver = Solver(package, pool, [], [futures, pre_commit], io)
    transaction = solver.solve(use_latest=[canonicalize_name("pre-commit")])

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": futures},
            {"job": "install", "package": pre_commit},
        ],
    )


def test_solver_should_not_raise_errors_for_irrelevant_transitive_python_constraints(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    package.python_versions = "~2.7 || ^3.5"
    set_package_python_versions(solver.provider, "~2.7 || ^3.5")
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


@pytest.mark.parametrize("is_locked", [False, True])
def test_solver_keeps_multiple_locked_dependencies_for_same_package(
    package: ProjectPackage,
    repo: Repository,
    pool: RepositoryPool,
    io: NullIO,
    is_locked: bool,
) -> None:
    package.add_dependency(
        Factory.create_dependency("A", {"version": "~1.1", "python": "<3.7"})
    )
    package.add_dependency(
        Factory.create_dependency("A", {"version": "~1.2", "python": ">=3.7"})
    )

    a11 = Package("A", "1.1")
    a12 = Package("A", "1.2")

    a11.add_dependency(Factory.create_dependency("B", {"version": ">=0.3"}))
    a12.add_dependency(Factory.create_dependency("B", {"version": ">=0.3"}))

    b03 = Package("B", "0.3")
    b04 = Package("B", "0.4")
    b04.python_versions = ">=3.6.2,<4.0.0"

    repo.add_package(a11)
    repo.add_package(a12)
    repo.add_package(b03)
    repo.add_package(b04)

    if is_locked:
        a11_locked = a11.clone()
        a11_locked.python_versions = "<3.7"
        a12_locked = a12.clone()
        a12_locked.python_versions = ">=3.7"
        locked = [a11_locked, a12_locked, b03.clone(), b04.clone()]
    else:
        locked = []

    solver = Solver(package, pool, [], locked, io)
    set_package_python_versions(solver.provider, "^3.6")
    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": b03},
            {"job": "install", "package": b04},
            {"job": "install", "package": a11},
            {"job": "install", "package": a12},
        ],
    )


@pytest.mark.parametrize("is_locked", [False, True])
def test_solver_does_not_update_ref_of_locked_vcs_package(
    package: ProjectPackage,
    repo: Repository,
    pool: RepositoryPool,
    io: NullIO,
    is_locked: bool,
) -> None:
    locked_ref = "123456"
    latest_ref = "9cf87a285a2d3fbb0b9fa621997b3acc3631ed24"
    demo_locked = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference=DEFAULT_SOURCE_REF,
        source_resolved_reference=locked_ref,
    )
    demo_locked.add_dependency(Factory.create_dependency("pendulum", "*"))
    demo_latest = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference=DEFAULT_SOURCE_REF,
        source_resolved_reference=latest_ref,
    )
    locked = [demo_locked] if is_locked else []

    package.add_dependency(
        Factory.create_dependency("demo", {"git": "https://github.com/demo/demo.git"})
    )

    # transient dependencies of demo
    pendulum = get_package("pendulum", "2.0.3")
    repo.add_package(pendulum)

    solver = Solver(package, pool, [], locked, io)
    transaction = solver.solve()

    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": pendulum},
            {"job": "install", "package": demo_locked if is_locked else demo_latest},
        ],
    )

    op = ops[1]

    assert op.package.source_type == "git"
    assert op.package.source_reference == DEFAULT_SOURCE_REF
    assert (
        op.package.source_resolved_reference == locked_ref if is_locked else latest_ref
    )


def test_solver_does_not_fetch_locked_vcs_package_with_ref(
    package: ProjectPackage,
    repo: Repository,
    pool: RepositoryPool,
    io: NullIO,
    mocker: MockerFixture,
) -> None:
    locked_ref = "123456"
    demo_locked = Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference=DEFAULT_SOURCE_REF,
        source_resolved_reference=locked_ref,
    )
    demo_locked.add_dependency(Factory.create_dependency("pendulum", "*"))

    package.add_dependency(
        Factory.create_dependency("demo", {"git": "https://github.com/demo/demo.git"})
    )

    # transient dependencies of demo
    pendulum = get_package("pendulum", "2.0.3")
    repo.add_package(pendulum)

    solver = Solver(package, pool, [], [demo_locked], io)
    spy = mocker.spy(solver._provider, "_search_for_vcs")

    solver.solve()

    spy.assert_not_called()


def test_solver_direct_origin_dependency_with_extras_requested_by_other_package(
    solver: Solver,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: FixtureDirGetter,
) -> None:
    """
    Another package requires the same dependency with extras that is required
    by the project as direct origin dependency without any extras.
    """
    pendulum = get_package("pendulum", "2.0.3")  # required by demo
    cleo = get_package("cleo", "1.0.0")  # required by demo[foo]
    demo_foo = get_package("demo-foo", "1.2.3")
    demo_foo.add_dependency(
        Factory.create_dependency("demo", {"version": ">=0.1", "extras": ["foo"]})
    )
    repo.add_package(demo_foo)
    repo.add_package(pendulum)
    repo.add_package(cleo)

    path = (fixture_dir("git") / "github.com" / "demo" / "demo").as_posix()

    # project requires path dependency of demo while demo-foo requires demo[foo]
    package.add_dependency(Factory.create_dependency("demo", {"path": path}))
    package.add_dependency(Factory.create_dependency("demo-foo", "^1.2.3"))

    transaction = solver.solve()

    demo = Package("demo", "0.1.2", source_type="directory", source_url=path)

    ops = check_solver_result(
        transaction,
        [
            {"job": "install", "package": cleo},
            {"job": "install", "package": pendulum},
            {"job": "install", "package": demo},
            {"job": "install", "package": demo_foo},
        ],
    )

    op = ops[2]

    assert op.package.name == "demo"
    assert op.package.version.text == "0.1.2"
    assert op.package.source_type == "directory"
    assert op.package.source_url == path


def test_solver_incompatible_dependency_with_and_without_extras(
    solver: Solver, repo: Repository, package: ProjectPackage
) -> None:
    """
    The solver first encounters a requirement for google-auth and then later an
    incompatible requirement for google-auth[aiohttp].

    Testcase derived from https://github.com/python-poetry/poetry/issues/6054.
    """
    # Incompatible requirements from foo and bar2.
    foo = get_package("foo", "1.0.0")
    foo.add_dependency(Factory.create_dependency("google-auth", {"version": "^1"}))

    bar = get_package("bar", "1.0.0")

    bar2 = get_package("bar", "2.0.0")
    bar2.add_dependency(
        Factory.create_dependency(
            "google-auth", {"version": "^2", "extras": ["aiohttp"]}
        )
    )

    baz = get_package("baz", "1.0.0")  # required by google-auth[aiohttp]

    google_auth = get_package("google-auth", "1.2.3")
    google_auth.extras = {canonicalize_name("aiohttp"): [get_dependency("baz", "^1.0")]}

    google_auth2 = get_package("google-auth", "2.3.4")
    google_auth2.extras = {
        canonicalize_name("aiohttp"): [get_dependency("baz", "^1.0")]
    }

    repo.add_package(foo)
    repo.add_package(bar)
    repo.add_package(bar2)
    repo.add_package(baz)
    repo.add_package(google_auth)
    repo.add_package(google_auth2)

    package.add_dependency(Factory.create_dependency("foo", ">=1"))
    package.add_dependency(Factory.create_dependency("bar", ">=1"))

    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": google_auth},
            {"job": "install", "package": bar},
            {"job": "install", "package": foo},
        ],
    )


def test_update_with_prerelease_and_no_solution(
    package: ProjectPackage, repo: Repository, pool: RepositoryPool, io: NullIO
) -> None:
    # Locked and installed: cleo which depends on an old version of crashtest.
    cleo = get_package("cleo", "1.0.0a5")
    crashtest = get_package("crashtest", "0.3.0")
    cleo.add_dependency(Factory.create_dependency("crashtest", {"version": "<0.4.0"}))
    installed = [cleo, crashtest]
    locked = [cleo, crashtest]

    # Try to upgrade to a new version of crashtest, this will be disallowed by the
    # dependency from cleo.
    package.add_dependency(Factory.create_dependency("cleo", "^1.0.0a5"))
    package.add_dependency(Factory.create_dependency("crashtest", "^0.4.0"))

    newer_crashtest = get_package("crashtest", "0.4.0")
    even_newer_crashtest = get_package("crashtest", "0.4.1")
    repo.add_package(cleo)
    repo.add_package(crashtest)
    repo.add_package(newer_crashtest)
    repo.add_package(even_newer_crashtest)

    solver = Solver(package, pool, installed, locked, io)

    with pytest.raises(SolverProblemError):
        solver.solve()


def test_solver_yanked_warning(
    package: ProjectPackage,
    pool: RepositoryPool,
    repo: Repository,
) -> None:
    package.add_dependency(Factory.create_dependency("foo", "==1"))
    package.add_dependency(Factory.create_dependency("bar", "==2"))
    package.add_dependency(Factory.create_dependency("baz", "==3"))
    foo = get_package("foo", "1", yanked=False)
    bar = get_package("bar", "2", yanked=True)
    baz = get_package("baz", "3", yanked="just wrong")
    repo.add_package(foo)
    repo.add_package(bar)
    repo.add_package(baz)

    io = BufferedIO(decorated=False)
    solver = Solver(package, pool, [], [], io)
    transaction = solver.solve()

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": bar},
            {"job": "install", "package": baz},
            {"job": "install", "package": foo},
        ],
    )
    error = io.fetch_error()
    assert "foo" not in error
    assert "The locked version 2 for bar is a yanked version." in error
    assert (
        "The locked version 3 for baz is a yanked version. Reason for being yanked:"
        " just wrong" in error
    )
    assert error.count("is a yanked version") == 2
    assert error.count("Reason for being yanked") == 1


@pytest.mark.parametrize("is_locked", [False, True])
def test_update_with_use_latest_vs_lock(
    package: ProjectPackage,
    repo: Repository,
    pool: RepositoryPool,
    io: NullIO,
    is_locked: bool,
) -> None:
    """
    A1 depends on B2, A2 and A3 depend on B1. Same for C.
    B1 depends on A2/C2, B2 depends on A1/C1.

    Because there are more versions of B than of A and C, B is resolved first
    so that latest version of B is used.
    There shouldn't be a difference between `poetry lock` (not is_locked)
    and `poetry update` (is_locked + use_latest)
    """
    # B added between A and C (and also alphabetically between)
    # to ensure that neither the first nor the last one is resolved first
    package.add_dependency(Factory.create_dependency("A", "*"))
    package.add_dependency(Factory.create_dependency("B", "*"))
    package.add_dependency(Factory.create_dependency("C", "*"))

    package_a1 = get_package("A", "1")
    package_a1.add_dependency(Factory.create_dependency("B", "3"))
    package_a2 = get_package("A", "2")
    package_a2.add_dependency(Factory.create_dependency("B", "1"))

    package_c1 = get_package("C", "1")
    package_c1.add_dependency(Factory.create_dependency("B", "3"))
    package_c2 = get_package("C", "2")
    package_c2.add_dependency(Factory.create_dependency("B", "1"))

    package_b1 = get_package("B", "1")
    package_b1.add_dependency(Factory.create_dependency("A", "2"))
    package_b1.add_dependency(Factory.create_dependency("C", "2"))
    package_b2 = get_package("B", "2")
    package_b2.add_dependency(Factory.create_dependency("A", "1"))
    package_b2.add_dependency(Factory.create_dependency("C", "1"))
    package_b3 = get_package("B", "3")
    package_b3.add_dependency(Factory.create_dependency("A", "1"))
    package_b3.add_dependency(Factory.create_dependency("C", "1"))

    repo.add_package(package_a1)
    repo.add_package(package_a2)
    repo.add_package(package_b1)
    repo.add_package(package_b2)
    repo.add_package(package_b3)
    repo.add_package(package_c1)
    repo.add_package(package_c2)

    if is_locked:
        locked = [package_a1, package_b3, package_c1]
        use_latest = [package.name for package in locked]
    else:
        locked = []
        use_latest = []

    solver = Solver(package, pool, [], locked, io)
    transaction = solver.solve(use_latest)

    check_solver_result(
        transaction,
        [
            {"job": "install", "package": package_c1},
            {"job": "install", "package": package_b3},
            {"job": "install", "package": package_a1},
        ],
    )


@pytest.mark.parametrize("with_extra", [False, True])
def test_solver_resolves_duplicate_dependency_in_extra(
    package: ProjectPackage,
    pool: RepositoryPool,
    repo: Repository,
    io: NullIO,
    with_extra: bool,
) -> None:
    """
    Without extras, a newer version of B can be chosen than with extras.
    See https://github.com/python-poetry/poetry/issues/8380.
    """
    constraint: dict[str, Any] = {"version": "*"}
    if with_extra:
        constraint["extras"] = ["foo"]
    package.add_dependency(Factory.create_dependency("A", constraint))

    package_a = get_package("A", "1.0")
    package_b1 = get_package("B", "1.0")
    package_b2 = get_package("B", "2.0")

    dep = get_dependency("B", ">=1.0")
    package_a.add_dependency(dep)

    dep_extra = get_dependency("B", "^1.0", optional=True)
    dep_extra.marker = parse_marker("extra == 'foo'")
    package_a.extras = {canonicalize_name("foo"): [dep_extra]}
    package_a.add_dependency(dep_extra)

    repo.add_package(package_a)
    repo.add_package(package_b1)
    repo.add_package(package_b2)

    solver = Solver(package, pool, [], [], io)
    transaction = solver.solve()

    check_solver_result(
        transaction,
        (
            [
                {"job": "install", "package": package_b1 if with_extra else package_b2},
                {"job": "install", "package": package_a},
            ]
        ),
    )


def test_solver_resolves_duplicate_dependencies_with_restricted_extras(
    package: ProjectPackage,
    pool: RepositoryPool,
    repo: Repository,
    io: NullIO,
) -> None:
    package.add_dependency(
        Factory.create_dependency("A", {"version": "*", "extras": ["foo"]})
    )

    package_a = get_package("A", "1.0")
    package_b1 = get_package("B", "1.0")
    package_b2 = get_package("B", "2.0")

    dep1 = get_dependency("B", "^1.0", optional=True)
    dep1.marker = parse_marker("sys_platform == 'win32' and extra == 'foo'")
    dep2 = get_dependency("B", "^2.0", optional=True)
    dep2.marker = parse_marker("sys_platform == 'linux' and extra == 'foo'")
    package_a.extras = {canonicalize_name("foo"): [dep1, dep2]}
    package_a.add_dependency(dep1)
    package_a.add_dependency(dep2)

    repo.add_package(package_a)
    repo.add_package(package_b1)
    repo.add_package(package_b2)

    solver = Solver(package, pool, [], [], io)
    transaction = solver.solve()

    check_solver_result(
        transaction,
        (
            [
                {"job": "install", "package": package_b1},
                {"job": "install", "package": package_b2},
                {"job": "install", "package": package_a},
            ]
        ),
    )
