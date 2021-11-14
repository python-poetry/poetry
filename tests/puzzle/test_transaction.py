from poetry.core.packages.package import Package
from poetry.puzzle.transaction import Transaction


def check_operations(ops, expected):
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

    assert expected == result


def test_it_should_calculate_operations_in_correct_order():
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


def test_it_should_calculate_operations_for_installed_packages():
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


def test_it_should_remove_installed_packages_if_required():
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


def test_it_should_update_installed_packages_if_sources_are_different():
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
