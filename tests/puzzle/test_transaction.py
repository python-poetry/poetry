from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from poetry.core.packages.package import Package

from poetry.installation.operations.update import Update
from poetry.puzzle.transaction import Transaction


if TYPE_CHECKING:
    from poetry.installation.operations.operation import Operation


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
        [
            (Package("a", "1.0.0"), 1),
            (Package("b", "2.1.0"), 2),
            (Package("d", "4.0.0"), 0),
        ],
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
        [
            (Package("a", "1.0.0"), 1),
            (Package("b", "2.1.0"), 2),
            (Package("d", "4.0.0"), 0),
        ],
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
        [
            (Package("a", "1.0.0"), 1),
            (Package("b", "2.1.0"), 2),
            (Package("d", "4.0.0"), 0),
        ],
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


def test_it_should_not_remove_installed_packages_that_are_in_result() -> None:
    transaction = Transaction(
        [],
        [
            (Package("a", "1.0.0"), 1),
            (Package("b", "2.0.0"), 2),
            (Package("c", "3.0.0"), 0),
        ],
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
        [
            (
                Package(
                    "a",
                    "1.0.0",
                    source_url="https://github.com/demo/demo.git",
                    source_type="git",
                    source_reference="main",
                    source_resolved_reference="123456",
                ),
                1,
            )
        ],
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
