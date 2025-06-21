from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import pytest

from packaging.utils import canonicalize_name
from poetry.core.packages.dependency import Dependency
from poetry.core.packages.dependency_group import MAIN_GROUP
from poetry.core.packages.package import Package
from poetry.core.packages.project_package import ProjectPackage
from poetry.core.version.markers import AnyMarker
from poetry.core.version.markers import parse_marker

from poetry.installation.operations.update import Update
from poetry.packages.transitive_package_info import TransitivePackageInfo
from poetry.puzzle.transaction import Transaction


if TYPE_CHECKING:
    from poetry.installation.operations.operation import Operation


DEV_GROUP = canonicalize_name("dev")


def get_transitive_info(depth: int) -> TransitivePackageInfo:
    return TransitivePackageInfo(depth, set(), {})


def check_operations(ops: list[Operation], expected: list[dict[str, Any]]) -> None:
    for e in expected:
        if "skipped" not in e:
            e["skipped"] = False

    result = []
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


def test_it_should_calculate_operations_in_correct_order() -> None:
    transaction = Transaction(
        [Package("a", "1.0.0"), Package("b", "2.0.0"), Package("c", "3.0.0")],
        {
            Package("a", "1.0.0"): get_transitive_info(1),
            Package("b", "2.1.0"): get_transitive_info(2),
            Package("d", "4.0.0"): get_transitive_info(0),
        },
    )

    check_operations(
        transaction.calculate_operations(),
        [
            {"job": "install", "package": Package("b", "2.1.0")},
            {"job": "install", "package": Package("a", "1.0.0")},
            {"job": "install", "package": Package("d", "4.0.0")},
        ],
    )


def test_it_should_calculate_operations_for_installed_packages() -> None:
    transaction = Transaction(
        [Package("a", "1.0.0"), Package("b", "2.0.0"), Package("c", "3.0.0")],
        {
            Package("a", "1.0.0"): get_transitive_info(1),
            Package("b", "2.1.0"): get_transitive_info(2),
            Package("d", "4.0.0"): get_transitive_info(0),
        },
        installed_packages=[
            Package("a", "1.0.0"),
            Package("b", "2.0.0"),
            Package("c", "3.0.0"),
            Package("e", "5.0.0"),
        ],
    )

    check_operations(
        transaction.calculate_operations(),
        [
            {"job": "remove", "package": Package("c", "3.0.0")},
            {
                "job": "update",
                "from": Package("b", "2.0.0"),
                "to": Package("b", "2.1.0"),
            },
            {"job": "install", "package": Package("a", "1.0.0"), "skipped": True},
            {"job": "install", "package": Package("d", "4.0.0")},
        ],
    )


def test_it_should_remove_installed_packages_if_required() -> None:
    transaction = Transaction(
        [Package("a", "1.0.0"), Package("b", "2.0.0"), Package("c", "3.0.0")],
        {
            Package("a", "1.0.0"): get_transitive_info(1),
            Package("b", "2.1.0"): get_transitive_info(2),
            Package("d", "4.0.0"): get_transitive_info(0),
        },
        installed_packages=[
            Package("a", "1.0.0"),
            Package("b", "2.0.0"),
            Package("c", "3.0.0"),
            Package("e", "5.0.0"),
        ],
    )

    check_operations(
        transaction.calculate_operations(synchronize=True),
        [
            {"job": "remove", "package": Package("c", "3.0.0")},
            {"job": "remove", "package": Package("e", "5.0.0")},
            {
                "job": "update",
                "from": Package("b", "2.0.0"),
                "to": Package("b", "2.1.0"),
            },
            {"job": "install", "package": Package("a", "1.0.0"), "skipped": True},
            {"job": "install", "package": Package("d", "4.0.0")},
        ],
    )


def test_it_should_not_remove_system_site_packages() -> None:
    """
    Different types of uninstalls:
    - c: tracked but not required
    - e: not tracked
    - f: root extra that is not requested
    """
    extra_name = canonicalize_name("foo")
    package = ProjectPackage("root", "1.0")
    dep_f = Dependency("f", "1", optional=True)
    dep_f._in_extras = [extra_name]
    package.add_dependency(dep_f)
    package.extras = {extra_name: [dep_f]}
    opt_f = Package("f", "6.0.0")
    opt_f.optional = True
    transaction = Transaction(
        [Package("a", "1.0.0"), Package("b", "2.0.0"), Package("c", "3.0.0")],
        {
            Package("a", "1.0.0"): get_transitive_info(1),
            Package("b", "2.1.0"): get_transitive_info(2),
            Package("d", "4.0.0"): get_transitive_info(0),
            opt_f: get_transitive_info(0),
        },
        installed_packages=[
            Package("a", "1.0.0"),
            Package("b", "2.0.0"),
            Package("c", "3.0.0"),
            Package("e", "5.0.0"),
            Package("f", "6.0.0"),
        ],
        root_package=package,
    )

    check_operations(
        transaction.calculate_operations(
            synchronize=True,
            extras=set(),
            system_site_packages={
                canonicalize_name(name) for name in ("a", "b", "c", "e", "f")
            },
        ),
        [
            {
                "job": "update",
                "from": Package("b", "2.0.0"),
                "to": Package("b", "2.1.0"),
            },
            {"job": "install", "package": Package("a", "1.0.0"), "skipped": True},
            {"job": "install", "package": Package("d", "4.0.0")},
        ],
    )


def test_it_should_not_remove_installed_packages_that_are_in_result() -> None:
    transaction = Transaction(
        [],
        {
            Package("a", "1.0.0"): get_transitive_info(1),
            Package("b", "2.0.0"): get_transitive_info(2),
            Package("c", "3.0.0"): get_transitive_info(0),
        },
        installed_packages=[
            Package("a", "1.0.0"),
            Package("b", "2.0.0"),
            Package("c", "3.0.0"),
        ],
    )

    check_operations(
        transaction.calculate_operations(synchronize=True),
        [
            {"job": "install", "package": Package("a", "1.0.0"), "skipped": True},
            {"job": "install", "package": Package("b", "2.0.0"), "skipped": True},
            {"job": "install", "package": Package("c", "3.0.0"), "skipped": True},
        ],
    )


def test_it_should_update_installed_packages_if_sources_are_different() -> None:
    transaction = Transaction(
        [Package("a", "1.0.0")],
        {
            Package(
                "a",
                "1.0.0",
                source_url="https://github.com/demo/demo.git",
                source_type="git",
                source_reference="main",
                source_resolved_reference="123456",
            ): get_transitive_info(1)
        },
        installed_packages=[Package("a", "1.0.0")],
    )

    check_operations(
        transaction.calculate_operations(synchronize=True),
        [
            {
                "job": "update",
                "from": Package("a", "1.0.0"),
                "to": Package(
                    "a",
                    "1.0.0",
                    source_url="https://github.com/demo/demo.git",
                    source_type="git",
                    source_reference="main",
                    source_resolved_reference="123456",
                ),
            }
        ],
    )


@pytest.mark.parametrize(
    ("groups", "expected"),
    [
        (set(), []),
        ({"main"}, ["a", "c"]),
        ({"dev"}, ["b", "c"]),
        ({"main", "dev"}, ["a", "b", "c"]),
    ],
)
@pytest.mark.parametrize("installed", [False, True])
@pytest.mark.parametrize("with_uninstalls", [False, True])
@pytest.mark.parametrize("sync", [False, True])
def test_calculate_operations_with_groups(
    installed: bool,
    with_uninstalls: bool,
    sync: bool,
    groups: set[str],
    expected: list[str],
) -> None:
    transaction = Transaction(
        [Package("a", "1"), Package("b", "1"), Package("c", "1"), Package("d", "1")],
        {
            Package("a", "1"): TransitivePackageInfo(
                0, {MAIN_GROUP}, {MAIN_GROUP: AnyMarker()}
            ),
            Package("b", "1"): TransitivePackageInfo(
                0, {DEV_GROUP}, {DEV_GROUP: AnyMarker()}
            ),
            Package("c", "1"): TransitivePackageInfo(
                0,
                {MAIN_GROUP, DEV_GROUP},
                {MAIN_GROUP: AnyMarker(), DEV_GROUP: AnyMarker()},
            ),
        },
        (
            [Package("a", "1"), Package("b", "1"), Package("c", "1"), Package("d", "1")]
            if installed
            else []
        ),
        None,
        {"python_version": "3.8"},
        {canonicalize_name(g) for g in groups},
    )

    expected_ops = [
        {"job": "install", "package": Package(name, "1")} for name in expected
    ]
    if installed:
        for op in expected_ops:
            op["skipped"] = True
        if with_uninstalls:
            expected_ops.insert(0, {"job": "remove", "package": Package("d", "1")})
            if sync:
                for name in sorted({"a", "b", "c"}.difference(expected), reverse=True):
                    expected_ops.insert(
                        0, {"job": "remove", "package": Package(name, "1")}
                    )

    check_operations(
        transaction.calculate_operations(
            with_uninstalls=with_uninstalls, synchronize=sync
        ),
        expected_ops,
    )


@pytest.mark.parametrize(
    ("python_version", "expected"), [("3.8", ["a"]), ("3.9", ["b"])]
)
@pytest.mark.parametrize("installed", [False, True])
@pytest.mark.parametrize("sync", [False, True])
def test_calculate_operations_with_markers(
    installed: bool, sync: bool, python_version: str, expected: list[str]
) -> None:
    transaction = Transaction(
        [Package("a", "1"), Package("b", "1")],
        {
            Package("a", "1"): TransitivePackageInfo(
                0, {MAIN_GROUP}, {MAIN_GROUP: parse_marker("python_version < '3.9'")}
            ),
            Package("b", "1"): TransitivePackageInfo(
                0, {MAIN_GROUP}, {MAIN_GROUP: parse_marker("python_version >= '3.9'")}
            ),
        },
        [Package("a", "1"), Package("b", "1")] if installed else [],
        None,
        {"python_version": python_version},
        {MAIN_GROUP},
    )

    expected_ops = [
        {"job": "install", "package": Package(name, "1")} for name in expected
    ]
    if installed:
        for op in expected_ops:
            op["skipped"] = True
        if sync:
            for name in sorted({"a", "b"}.difference(expected), reverse=True):
                expected_ops.insert(0, {"job": "remove", "package": Package(name, "1")})

    check_operations(
        transaction.calculate_operations(with_uninstalls=sync, synchronize=sync),
        expected_ops,
    )


@pytest.mark.parametrize(
    ("python_version", "sys_platform", "groups", "expected"),
    [
        ("3.8", "win32", {"main"}, True),
        ("3.9", "linux", {"main"}, False),
        ("3.9", "linux", {"dev"}, True),
        ("3.8", "win32", {"dev"}, False),
        ("3.9", "linux", {"main", "dev"}, True),
        ("3.8", "win32", {"main", "dev"}, True),
        ("3.8", "linux", {"main", "dev"}, True),
        ("3.9", "win32", {"main", "dev"}, False),
    ],
)
def test_calculate_operations_with_groups_and_markers(
    python_version: str,
    sys_platform: str,
    groups: set[str],
    expected: bool,
) -> None:
    transaction = Transaction(
        [Package("a", "1")],
        {
            Package("a", "1"): TransitivePackageInfo(
                0,
                {MAIN_GROUP, DEV_GROUP},
                {
                    MAIN_GROUP: parse_marker("python_version < '3.9'"),
                    DEV_GROUP: parse_marker("sys_platform == 'linux'"),
                },
            ),
        },
        [],
        None,
        {"python_version": python_version, "sys_platform": sys_platform},
        {canonicalize_name(g) for g in groups},
    )

    expected_ops = (
        [{"job": "install", "package": Package("a", "1")}] if expected else []
    )

    check_operations(transaction.calculate_operations(), expected_ops)


@pytest.mark.parametrize("extras", [False, True])
@pytest.mark.parametrize("marker_env", [False, True])
@pytest.mark.parametrize("installed", [False, True])
@pytest.mark.parametrize("with_uninstalls", [False, True])
@pytest.mark.parametrize("sync", [False, True])
def test_calculate_operations_extras(
    extras: bool,
    marker_env: bool,
    installed: bool,
    with_uninstalls: bool,
    sync: bool,
) -> None:
    extra_name = canonicalize_name("foo")
    package = ProjectPackage("root", "1.0")
    dep_a = Dependency("a", "1", optional=True)
    dep_a._in_extras = [extra_name]
    package.add_dependency(dep_a)
    package.extras = {extra_name: [dep_a]}
    opt_a = Package("a", "1")
    opt_a.optional = True

    transaction = Transaction(
        [Package("a", "1")],
        {
            opt_a: TransitivePackageInfo(
                0,
                {MAIN_GROUP} if marker_env else set(),
                {MAIN_GROUP: parse_marker("extra == 'foo'")} if marker_env else {},
            )
        },
        [Package("a", "1")] if installed else [],
        package,
        {"python_version": "3.8"} if marker_env else None,
        {MAIN_GROUP} if marker_env else None,
    )

    if extras:
        ops = [{"job": "install", "package": Package("a", "1"), "skipped": installed}]
    elif installed:
        if with_uninstalls and sync:
            ops = [{"job": "remove", "package": Package("a", "1")}]
        else:
            ops = []
    else:
        ops = [{"job": "install", "package": Package("a", "1"), "skipped": True}]

    check_operations(
        transaction.calculate_operations(
            with_uninstalls=with_uninstalls,
            synchronize=sync,
            extras={extra_name} if extras else set(),
        ),
        ops,
    )


@pytest.mark.parametrize("extra", ["", "foo", "bar"])
def test_calculate_operations_extras_no_redundant_uninstall(extra: str) -> None:
    extra1 = canonicalize_name("foo")
    extra2 = canonicalize_name("bar")
    package = ProjectPackage("root", "1.0")
    dep_a1 = Dependency("a", "1", optional=True)
    dep_a1._in_extras = [canonicalize_name("foo")]
    dep_a1.marker = parse_marker("extra != 'bar'")
    dep_a2 = Dependency("a", "2", optional=True)
    dep_a2._in_extras = [canonicalize_name("bar")]
    dep_a2.marker = parse_marker("extra != 'foo'")
    package.add_dependency(dep_a1)
    package.add_dependency(dep_a2)
    package.extras = {extra1: [dep_a1], extra2: [dep_a2]}
    opt_a1 = Package("a", "1")
    opt_a1.optional = True
    opt_a2 = Package("a", "2")
    opt_a2.optional = True

    transaction = Transaction(
        [Package("a", "1")],
        {
            opt_a1: TransitivePackageInfo(
                0,
                {MAIN_GROUP},
                {MAIN_GROUP: parse_marker("extra == 'foo' and extra != 'bar'")},
            ),
            opt_a2: TransitivePackageInfo(
                0,
                {MAIN_GROUP},
                {MAIN_GROUP: parse_marker("extra == 'bar' and extra != 'foo'")},
            ),
        },
        [Package("a", "1")],
        package,
        {"python_version": "3.9"},
        {MAIN_GROUP},
    )

    if not extra:
        ops = [{"job": "remove", "package": Package("a", "1")}]
    elif extra == "foo":
        ops = [{"job": "install", "package": Package("a", "1"), "skipped": True}]
    elif extra == "bar":
        ops = [{"job": "update", "from": Package("a", "1"), "to": Package("a", "2")}]
    else:
        raise NotImplementedError

    check_operations(
        transaction.calculate_operations(
            synchronize=True,
            extras=set() if not extra else {canonicalize_name(extra)},
        ),
        ops,
    )
