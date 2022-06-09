from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.core.packages.dependency_group import MAIN_GROUP
from poetry.core.packages.dependency_group import DependencyGroup

from poetry.factory import Factory
from tests.helpers import get_package


if TYPE_CHECKING:
    from typing import Any

    from cleo.testers.command_tester import CommandTester
    from poetry.core.packages.package import Package

    from poetry.poetry import Poetry
    from poetry.repositories import Repository
    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("show")


def mock_install(repo: Repository, packages: list[Package]):
    for package in packages:
        repo.add_package(package)


def mock_poetry_dependency(
    poetry: Poetry, package: Package, groups: list[str] | None = None
) -> None:
    poetry.package.add_dependency(
        Factory.create_dependency(package.name, f"^{package.version}", groups=groups)
    )


@pytest.fixture()
def cachy_010(poetry: Poetry) -> Package:
    return get_package("cachy", "0.1.0", description="Cachy package")


@pytest.fixture()
def pendulum_200(poetry: Poetry) -> Package:
    return get_package("pendulum", "2.0.0", description="Pendulum package")


@pytest.fixture()
def pytest_373(poetry: Poetry) -> Package:
    return get_package("pytest", "3.7.3", description="Pytest package")


def _mock_lock_package(package: Package, override: dict | None = None) -> dict:
    package_lock = {
        "name": package.name,
        "version": str(package.version),
        "description": package.description,
        "category": package.category,
        "optional": package.optional,
        "platform": "*",
        "python-versions": "*",
        "checksum": [],
    }
    for group in package._dependency_groups.values():
        package_lock["dependencies"] = {
            dependency.name: dependency.pretty_constraint
            for dependency in group.dependencies
        }
    if override is not None:
        package_lock.update(override)
    return package_lock


def mock_lock_data(
    poetry: Poetry, packages: list[Package], override: dict[str, Any] = None
) -> None:
    override = override or {}
    lockfile = {
        "package": [
            _mock_lock_package(package, override.get(package.name))
            for package in packages
        ],
        "metadata": {
            "python-versions": "*",
            "platform": "*",
            "content-hash": "123456789",
            "hashes": {package.name: [] for package in packages},
        },
    }
    poetry.locker.mock_lock_data(lockfile)


def test_show_basic_with_installed_packages(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    cachy_010: Package,
    pendulum_200: Package,
    pytest_373: Package,
):
    mock_poetry_dependency(poetry, cachy_010)
    mock_poetry_dependency(poetry, pendulum_200)
    mock_poetry_dependency(poetry, pytest_373)
    packages = [cachy_010, pendulum_200, pytest_373]

    mock_install(installed, packages)
    mock_lock_data(poetry, packages)

    tester.execute()

    expected = """\
cachy    0.1.0 Cachy package
pendulum 2.0.0 Pendulum package
pytest   3.7.3 Pytest package
"""

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        (
            "",
            """\
cachy  0.1.0 Cachy package
pytest 3.7.3 Pytest package
""",
        ),
        (
            "--with time",
            """\
cachy    0.1.0 Cachy package
pendulum 2.0.0 Pendulum package
pytest   3.7.3 Pytest package
""",
        ),
        (
            "--without test",
            """\
cachy 0.1.0 Cachy package
""",
        ),
        (
            f"--without {MAIN_GROUP}",
            """\
pytest 3.7.3 Pytest package
""",
        ),
        (
            f"--only {MAIN_GROUP}",
            """\
cachy 0.1.0 Cachy package
""",
        ),
        (
            "--default",
            """\
cachy 0.1.0 Cachy package
""",
        ),
        (
            "--no-dev",
            """\
cachy 0.1.0 Cachy package
""",
        ),
        (
            "--with time --without test",
            """\
cachy    0.1.0 Cachy package
pendulum 2.0.0 Pendulum package
""",
        ),
        (
            f"--with time --without {MAIN_GROUP},test",
            """\
pendulum 2.0.0 Pendulum package
""",
        ),
        (
            "--only time",
            """\
pendulum 2.0.0 Pendulum package
""",
        ),
        (
            "--only time --with test",
            """\
pendulum 2.0.0 Pendulum package
""",
        ),
        (
            "--with time",
            """\
cachy    0.1.0 Cachy package
pendulum 2.0.0 Pendulum package
pytest   3.7.3 Pytest package
""",
        ),
    ],
)
def test_show_basic_with_group_options(
    options: str,
    expected: str,
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    cachy_010: Package,
):
    pendulum_200 = get_package(
        "pendulum", "2.0.0", description="Pendulum package", category="dev"
    )
    pytest_373 = get_package(
        "pytest", "3.7.3", description="Pytest package", category="dev"
    )

    poetry.package.add_dependency_group(DependencyGroup(name="time", optional=True))

    mock_poetry_dependency(poetry, cachy_010)
    mock_poetry_dependency(poetry, pendulum_200, groups=["time"])
    mock_poetry_dependency(poetry, pytest_373, groups=["test"])

    packages = [cachy_010, pendulum_200, pytest_373]

    mock_install(installed, packages)
    mock_lock_data(poetry, packages)

    tester.execute(options)

    assert tester.io.fetch_output() == expected


def test_show_basic_with_installed_packages_single(
    tester: CommandTester, poetry: Poetry, installed: Repository, cachy_010: Package
):
    mock_poetry_dependency(poetry, cachy_010)
    packages = [cachy_010]

    mock_install(installed, packages)
    mock_lock_data(poetry, packages)

    tester.execute("cachy")

    assert [
        "name         : cachy",
        "version      : 0.1.0",
        "description  : Cachy package",
    ] == [line.strip() for line in tester.io.fetch_output().splitlines()]


def test_show_basic_with_installed_packages_single_canonicalized(
    tester: CommandTester, poetry: Poetry, installed: Repository
):
    foo_bar = get_package("foo-bar", "0.1.0", description="Foobar package")
    mock_poetry_dependency(poetry, foo_bar)
    packages = [foo_bar]
    mock_install(installed, packages)
    mock_lock_data(poetry, packages)

    tester.execute("Foo_Bar")

    assert [
        "name         : foo-bar",
        "version      : 0.1.0",
        "description  : Foobar package",
    ] == [line.strip() for line in tester.io.fetch_output().splitlines()]


@pytest.mark.parametrize(
    ("decorated", "expected"),
    [
        (
            False,
            """\
cachy        0.1.0 Cachy package
pendulum (!) 2.0.0 Pendulum package
""",
        ),
        (
            True,
            """\
\033[36mcachy   \033[39m \033[39;1m0.1.0\033[39;22m Cachy package
\033[31mpendulum\033[39m \033[39;1m2.0.0\033[39;22m Pendulum package
""",
        ),
    ],
)
def test_show_basic_with_not_installed_packages_decorations(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    decorated: bool,
    expected: str,
    cachy_010: Package,
    pendulum_200: Package,
):
    mock_poetry_dependency(poetry, cachy_010)
    mock_poetry_dependency(poetry, pendulum_200)
    mock_install(installed, [cachy_010])
    mock_lock_data(poetry, [cachy_010, pendulum_200])

    tester.execute(decorated=decorated)

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    ("decorated", "expected"),
    [
        (
            False,
            """\
cachy    0.1.0 0.2.0 Cachy package
pendulum 2.0.0 2.0.1 Pendulum package
""",
        ),
        (
            True,
            """\
\033[36mcachy   \033[39m \033[39;1m0.1.0\033[39;22m\
 \033[33m0.2.0\033[39m Cachy package
\033[36mpendulum\033[39m \033[39;1m2.0.0\033[39;22m\
 \033[31m2.0.1\033[39m Pendulum package
""",
        ),
    ],
)
def test_show_latest_decorations(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
    decorated: bool,
    expected: str,
    cachy_010: Package,
    pendulum_200: Package,
):
    mock_poetry_dependency(poetry, cachy_010)
    mock_poetry_dependency(poetry, pendulum_200)
    installed_packages = [cachy_010, pendulum_200]
    new_packages = [
        get_package("cachy", "0.2.0", description="Cachy package"),
        get_package("pendulum", "2.0.1", description="Cachy package"),
    ]
    mock_install(installed, installed_packages)
    mock_install(repo, installed_packages + new_packages)
    mock_lock_data(poetry, installed_packages)

    tester.execute("--latest", decorated=decorated)

    assert tester.io.fetch_output() == expected


def test_show_outdated(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
    cachy_010: Package,
    pendulum_200: Package,
):
    mock_poetry_dependency(poetry, cachy_010)
    mock_poetry_dependency(poetry, pendulum_200)
    installed_packages = [cachy_010, pendulum_200]
    new_packages = [
        get_package("cachy", "0.2.0", description="Cachy package"),
    ]
    mock_install(installed, installed_packages)
    mock_install(repo, installed_packages + new_packages)
    mock_lock_data(poetry, installed_packages)

    tester.execute("--outdated")

    expected = """\
cachy 0.1.0 0.2.0 Cachy package
"""

    assert tester.io.fetch_output() == expected


def test_show_outdated_with_only_up_to_date_packages(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
    cachy_010: Package,
):
    mock_poetry_dependency(poetry, cachy_010)
    packages = [cachy_010]
    mock_install(installed, packages)
    mock_install(repo, packages)
    mock_lock_data(poetry, packages)

    tester.execute("--outdated")

    expected = ""

    assert tester.io.fetch_output() == expected


def test_show_outdated_has_prerelease_but_not_allowed(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
    cachy_010: Package,
    pendulum_200: Package,
):
    mock_poetry_dependency(poetry, cachy_010)
    mock_poetry_dependency(poetry, pendulum_200)
    installed_packages = [cachy_010, pendulum_200]
    new_packages = [
        get_package("cachy", "0.2.0", description="Cachy package"),
        get_package("cachy", "0.3.0.dev123", description="Cachy package"),
    ]
    mock_install(installed, installed_packages)
    mock_install(repo, installed_packages + new_packages)
    mock_lock_data(poetry, installed_packages)

    tester.execute("--outdated")

    expected = """\
cachy 0.1.0 0.2.0 Cachy package
"""

    assert tester.io.fetch_output() == expected


def test_show_outdated_has_prerelease_and_allowed(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
    pendulum_200: Package,
):
    mock_poetry_dependency(poetry, pendulum_200)
    poetry.package.add_dependency(
        Factory.create_dependency(
            "cachy", {"version": ">=0.0.1", "allow-prereleases": True}
        )
    )

    cachy_010dev = get_package("cachy", "0.1.0.dev1", description="Cachy package")
    cachy_020 = get_package("cachy", "0.2.0", description="Cachy package")
    cachy_030dev = get_package("cachy", "0.3.0.dev123", description="Cachy package")

    mock_install(installed, [cachy_010dev, pendulum_200])
    # sorting isn't used, so cachy_030dev has to be the first element to
    # replicate the issue in PR #1548
    mock_install(repo, [cachy_030dev, cachy_020, cachy_010dev, pendulum_200])

    mock_lock_data(poetry, [cachy_010dev, pendulum_200])

    tester.execute("--outdated")

    expected = """\
cachy 0.1.0.dev1 0.3.0.dev123 Cachy package
"""

    assert tester.io.fetch_output() == expected


def test_show_outdated_formatting(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
    cachy_010: Package,
    pendulum_200: Package,
):
    mock_poetry_dependency(poetry, cachy_010)
    mock_poetry_dependency(poetry, pendulum_200)
    installed_packages = [cachy_010, pendulum_200]
    new_packages = [
        get_package("cachy", "0.2.0"),
        get_package("pendulum", "2.0.1"),
    ]
    mock_install(installed, installed_packages)
    mock_install(repo, installed_packages + new_packages)
    mock_lock_data(poetry, installed_packages)

    tester.execute("--outdated")

    expected = """\
cachy    0.1.0 0.2.0 Cachy package
pendulum 2.0.0 2.0.1 Pendulum package
"""

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    ("project_directory", "required_fixtures"),
    [
        (
            "project_with_local_dependencies",
            ["distributions/demo-0.1.0-py2.py3-none-any.whl", "project_with_setup"],
        ),
    ],
)
def test_show_outdated_local_dependencies(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
):
    installed_packages = [
        get_package("cachy", "0.2.0"),
        get_package("pendulum", "2.0.0"),
    ]
    demo = get_package("demo", "0.1.0")
    project_with_setup = get_package(
        "project-with-setup", "0.1.1", description="Demo project."
    )
    local_packages = [
        demo,
        project_with_setup,
    ]
    new_packages = [get_package("cachy", "0.3.0", description="Cachy package")]
    mock_install(installed, installed_packages + local_packages)
    mock_install(repo, installed_packages + new_packages)
    mock_lock_data(
        poetry,
        installed_packages + local_packages,
        override={
            "demo": {
                "source": {
                    "type": "file",
                    "reference": "",
                    "url": "../distributions/demo-0.1.0-py2.py3-none-any.whl",
                },
            },
            "project-with-setup": {
                "source": {
                    "type": "directory",
                    "reference": "",
                    "url": "../project_with_setup",
                },
                "dependencies": {
                    "pendulum": "pendulum>=1.4.4",
                    "cachy": {"version": ">=0.2.0", "extras": ["msgpack"]},
                },
            },
        },
    )

    tester.execute("--outdated")

    expected = """\
cachy              0.2.0                       0.3.0
project-with-setup 0.1.1 ../project_with_setup 0.1.2 ../project_with_setup
"""
    assert (
        "\n".join(line.rstrip() for line in tester.io.fetch_output().splitlines())
        == expected.rstrip()
    )


@pytest.mark.parametrize("project_directory", ["project_with_git_dev_dependency"])
@pytest.mark.parametrize(
    ("category", "option", "expected"),
    [
        (
            "main",
            "--outdated",
            """\
cachy 0.1.0         0.2.0         Cachy package
demo  0.1.1 9cf87a2 0.1.2 9cf87a2 Demo package
""",
        ),
        (
            "dev",
            "--outdated --without dev",
            """\
cachy 0.1.0 0.2.0 Cachy package
""",
        ),
    ],
)
def test_show_outdated_git_dev_dependency(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
    category: str,
    option: str,
    expected: str,
    cachy_010: Package,
    pendulum_200: Package,
):
    pytest_343 = get_package("pytest", "3.4.3")
    installed_packages = [cachy_010, pendulum_200, pytest_343]
    git_packages = [
        get_package("demo", "0.1.1", category=category, description="Demo package")
    ]
    new_packages = [get_package("cachy", "0.2.0", category=category)]
    mock_install(installed, installed_packages + git_packages)
    mock_install(repo, installed_packages + new_packages)
    mock_lock_data(
        poetry,
        installed_packages + git_packages,
        override={
            "demo": {
                "source": {
                    "type": "git",
                    "reference": "9cf87a285a2d3fbb0b9fa621997b3acc3631ed24",
                    "resolved_reference": "9cf87a285a2d3fbb0b9fa621997b3acc3631ed24",
                    "url": "https://github.com/demo/demo.git",
                }
            }
        },
    )

    tester.execute(option)

    assert tester.io.fetch_output() == expected


def test_show_hides_incompatible_package(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    cachy_010: Package,
    pendulum_200: Package,
):
    poetry.package.add_dependency(
        Factory.create_dependency("cachy", {"version": "^0.1.0", "python": "< 2.0"})
    )
    mock_poetry_dependency(poetry, pendulum_200)
    packages = [cachy_010, pendulum_200]
    mock_install(installed, packages)
    mock_lock_data(poetry, packages)

    tester.execute()

    expected = """\
pendulum 2.0.0 Pendulum package
"""

    assert tester.io.fetch_output() == expected


def test_show_all_shows_incompatible_package(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
    cachy_010: Package,
    pendulum_200: Package,
):
    installed.add_package(pendulum_200)
    mock_lock_data(
        poetry,
        [cachy_010, pendulum_200],
        override={"cachy": {"requirements": {"python": "1.0"}}},
    )

    tester.execute("--all")

    expected = """\
cachy     0.1.0 Cachy package
pendulum  2.0.0 Pendulum package
"""

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    ("option", "expected"),
    [
        (
            "--without dev",
            """\
cachy    0.1.0 Cachy package
pendulum 2.0.0 Pendulum package
""",
        ),
        (
            "--only dev",
            """\
pytest 3.7.3 Pytest package
""",
        ),
    ],
)
def test_show_non_dev_with_without_basic_installed_packages(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    option: str,
    expected: str,
    cachy_010: Package,
    pendulum_200: Package,
    pytest_373: Package,
):
    mock_poetry_dependency(poetry, cachy_010)
    mock_poetry_dependency(poetry, pendulum_200)
    poetry.package.add_dependency(
        Factory.create_dependency("pytest", "*", groups=["dev"])
    )

    pytest_373.category = "dev"

    packages = [cachy_010, pendulum_200, pytest_373]
    mock_install(installed, packages)
    mock_lock_data(poetry, packages)

    tester.execute(option)

    assert tester.io.fetch_output() == expected


def test_show_with_optional_group(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    cachy_010: Package,
    pendulum_200: Package,
    pytest_373: Package,
):
    mock_poetry_dependency(poetry, cachy_010)
    mock_poetry_dependency(poetry, pendulum_200)
    group = DependencyGroup("dev", optional=True)
    group.add_dependency(Factory.create_dependency("pytest", "*", groups=["dev"]))
    poetry.package.add_dependency_group(group)

    pytest_373.category = "dev"
    packages = [
        cachy_010,
        pendulum_200,
        pytest_373,
    ]
    mock_install(installed, packages)
    mock_lock_data(poetry, packages)

    tester.execute()

    expected = """\
cachy    0.1.0 Cachy package
pendulum 2.0.0 Pendulum package
"""

    assert tester.io.fetch_output() == expected

    tester.execute("--with dev")

    expected = """\
cachy    0.1.0 Cachy package
pendulum 2.0.0 Pendulum package
pytest   3.7.3 Pytest package
"""

    assert tester.io.fetch_output() == expected


def test_show_tree(tester: CommandTester, poetry: Poetry, installed: Repository):
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.2.0"))
    cachy2 = get_package("cachy", "0.2.0")
    msgpack_python051 = get_package("msgpack-python", "0.5.1")

    cachy2.add_dependency(Factory.create_dependency("msgpack-python", ">=0.5 <0.6"))

    mock_install(installed, [cachy2])
    mock_lock_data(poetry, [cachy2, msgpack_python051])

    tester.execute("--tree", supports_utf8=False)

    expected = """\
cachy 0.2.0
`-- msgpack-python >=0.5 <0.6
"""

    assert tester.io.fetch_output() == expected


def test_show_tree_no_dev(tester: CommandTester, poetry: Poetry, installed: Repository):
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.2.0"))
    poetry.package.add_dependency(
        Factory.create_dependency("pytest", "^6.1.0", groups=["dev"])
    )
    cachy2 = get_package("cachy", "0.2.0", description="")
    pytest610 = get_package("pytest", "6.1.0", category="dev")
    msgpack_python051 = get_package("msgpack-python", "0.5.1")

    cachy2.add_dependency(Factory.create_dependency("msgpack-python", ">=0.5 <0.6"))

    mock_install(installed, [cachy2, pytest610])
    mock_lock_data(poetry, [cachy2, pytest610, msgpack_python051])

    tester.execute("--tree --without dev")

    expected = """\
cachy 0.2.0
└── msgpack-python >=0.5 <0.6
"""

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    ("option", "expected"),
    [
        (
            "--tree --why b",
            """\
a 0.0.1
└── b =0.0.1
    └── c =0.0.1 \n""",
        ),
        (
            "--why",
            # this has to be on a single line due to the padding
            # whitespace, which gets stripped by pre-commit.
            """a 0.0.1        \nb 0.0.1 from a \nc 0.0.1 from b \n""",
        ),
    ],
)
def test_show_tree_why_package(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    option: str,
    expected: str,
):
    poetry.package.add_dependency(Factory.create_dependency("a", "=0.0.1"))

    a = get_package("a", "0.0.1")
    installed.add_package(a)
    a.add_dependency(Factory.create_dependency("b", "=0.0.1"))

    b = get_package("b", "0.0.1")
    b.add_dependency(Factory.create_dependency("c", "=0.0.1"))
    installed.add_package(b)

    c = get_package("c", "0.0.1")
    installed.add_package(c)

    mock_lock_data(poetry, [a, b, c])

    tester.execute(option)

    assert tester.io.fetch_output() == expected


def test_show_required_by_deps(
    tester: CommandTester, poetry: Poetry, installed: Repository
):
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.2.0"))
    poetry.package.add_dependency(Factory.create_dependency("pendulum", "2.0.0"))

    cachy2 = get_package("cachy", "0.2.0")
    cachy2.add_dependency(Factory.create_dependency("msgpack-python", ">=0.5 <0.6"))

    pendulum = get_package("pendulum", "2.0.0")
    pendulum.add_dependency(Factory.create_dependency("CachY", ">=0.2.0 <0.3.0"))

    msgpack_python = get_package("msgpack-python", "0.5.1")

    installed.add_package(cachy2)
    installed.add_package(pendulum)

    mock_lock_data(poetry, [cachy2, pendulum, msgpack_python])

    tester.execute("cachy")

    expected = """\
 name         : cachy
 version      : 0.2.0
 description  :

dependencies
 - msgpack-python >=0.5 <0.6

required by
 - pendulum >=0.2.0 <0.3.0
""".splitlines()
    actual = [line.rstrip() for line in tester.io.fetch_output().splitlines()]
    assert actual == expected


def test_show_errors_without_lock_file(tester: CommandTester, poetry: Poetry):
    assert not poetry.locker.lock.exists()

    tester.execute()

    expected = "Error: poetry.lock not found. Run `poetry lock` to create it.\n"
    assert tester.io.fetch_error() == expected
    assert tester.status_code == 1
