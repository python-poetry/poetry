from __future__ import annotations

import json

from typing import TYPE_CHECKING

import pytest

from poetry.core.packages.dependency_group import MAIN_GROUP
from poetry.core.packages.dependency_group import DependencyGroup

from poetry.factory import Factory
from poetry.utils._compat import tomllib
from tests.helpers import MOCK_DEFAULT_GIT_REVISION
from tests.helpers import TestLocker
from tests.helpers import get_package


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.poetry import Poetry
    from poetry.repositories import Repository
    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("show")


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        (
            "",
            """\
cachy    0.1.0 Cachy package
pendulum 2.0.0 Pendulum package
pytest   3.7.3 Pytest package
""",
        ),
        (
            "--output json",
            [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "installed_status": "installed",
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "installed_status": "installed",
                },
                {
                    "name": "pytest",
                    "version": "3.7.3",
                    "description": "Pytest package",
                    "installed_status": "installed",
                },
            ],
        ),
    ],
)
def test_show_basic_with_installed_packages(
    options: str,
    expected: str,
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.1.0"))
    poetry.package.add_dependency(Factory.create_dependency("pendulum", "^2.0.0"))
    poetry.package.add_dependency(
        Factory.create_dependency("pytest", "^3.7.3", groups=["dev"])
    )

    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    pytest_373 = get_package("pytest", "3.7.3")
    pytest_373.description = "Pytest package"

    installed.add_package(cachy_010)
    installed.add_package(pendulum_200)
    installed.add_package(pytest_373)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pytest",
                    "version": "3.7.3",
                    "description": "Pytest package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": [], "pytest": []},
            },
        }
    )

    tester.execute(options)

    if options:
        assert json.loads(tester.io.fetch_output()) == expected
    else:
        assert tester.io.fetch_output() == expected


def _configure_project_with_groups(poetry: Poetry, installed: Repository) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.1.0"))

    poetry.package.add_dependency_group(DependencyGroup(name="time", optional=True))
    poetry.package.add_dependency(
        Factory.create_dependency("pendulum", "^2.0.0", groups=["time"])
    )

    poetry.package.add_dependency(
        Factory.create_dependency("pytest", "^3.7.3", groups=["test"])
    )

    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    pytest_373 = get_package("pytest", "3.7.3")
    pytest_373.description = "Pytest package"

    installed.add_package(cachy_010)
    installed.add_package(pendulum_200)
    installed.add_package(pytest_373)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pytest",
                    "version": "3.7.3",
                    "description": "Pytest package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": [], "pytest": []},
            },
        }
    )


@pytest.mark.parametrize(
    ("options", "expected", "is_json"),
    [
        (
            "",
            """\
cachy  0.1.0 Cachy package
pytest 3.7.3 Pytest package
""",
            False,
        ),
        (
            "--output json",
            [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "installed_status": "installed",
                },
                {
                    "name": "pytest",
                    "version": "3.7.3",
                    "description": "Pytest package",
                    "installed_status": "installed",
                },
            ],
            True,
        ),
        (
            "--with time",
            """\
cachy    0.1.0 Cachy package
pendulum 2.0.0 Pendulum package
pytest   3.7.3 Pytest package
""",
            False,
        ),
        (
            "--with time --output json",
            [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "installed_status": "installed",
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "installed_status": "installed",
                },
                {
                    "name": "pytest",
                    "version": "3.7.3",
                    "description": "Pytest package",
                    "installed_status": "installed",
                },
            ],
            True,
        ),
        (
            "--without test",
            """\
cachy 0.1.0 Cachy package
""",
            False,
        ),
        (
            "--without test --output json",
            [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "installed_status": "installed",
                },
            ],
            True,
        ),
        (
            f"--without {MAIN_GROUP}",
            """\
pytest 3.7.3 Pytest package
""",
            False,
        ),
        (
            f"--without {MAIN_GROUP} --output json",
            [
                {
                    "name": "pytest",
                    "version": "3.7.3",
                    "description": "Pytest package",
                    "installed_status": "installed",
                },
            ],
            True,
        ),
        (
            f"--only {MAIN_GROUP}",
            """\
cachy 0.1.0 Cachy package
""",
            False,
        ),
        (
            f"--only {MAIN_GROUP} --output json",
            [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "installed_status": "installed",
                },
            ],
            True,
        ),
        (
            "--with time --without test",
            """\
cachy    0.1.0 Cachy package
pendulum 2.0.0 Pendulum package
""",
            False,
        ),
        (
            "--with time --without test --output json",
            [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "installed_status": "installed",
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "installed_status": "installed",
                },
            ],
            True,
        ),
        (
            f"--with time --without {MAIN_GROUP},test",
            """\
pendulum 2.0.0 Pendulum package
""",
            False,
        ),
        (
            f"--with time --without {MAIN_GROUP},test --output json",
            [
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "installed_status": "installed",
                },
            ],
            True,
        ),
        (
            "--only time",
            """\
pendulum 2.0.0 Pendulum package
""",
            False,
        ),
        (
            "--only time --output json",
            [
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "installed_status": "installed",
                },
            ],
            True,
        ),
        (
            "--only time --with test",
            """\
pendulum 2.0.0 Pendulum package
""",
            False,
        ),
        (
            "--only time --with test --output json",
            [
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "installed_status": "installed",
                },
            ],
            True,
        ),
        (
            "--with time",
            """\
cachy    0.1.0 Cachy package
pendulum 2.0.0 Pendulum package
pytest   3.7.3 Pytest package
""",
            False,
        ),
        (
            "--with time --output json",
            [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "installed_status": "installed",
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "installed_status": "installed",
                },
                {
                    "name": "pytest",
                    "version": "3.7.3",
                    "description": "Pytest package",
                    "installed_status": "installed",
                },
            ],
            True,
        ),
    ],
)
def test_show_basic_with_group_options(
    options: str,
    expected: str,
    is_json: bool,
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
) -> None:
    _configure_project_with_groups(poetry, installed)

    tester.execute(options)

    if is_json:
        assert json.loads(tester.io.fetch_output()) == expected
    else:
        assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    ("expected", "output_format"),
    [
        (
            [
                "name         : cachy",
                "version      : 0.1.0",
                "description  : Cachy package",
            ],
            "",
        ),
        (
            {"name": "cachy", "version": "0.1.0", "description": "Cachy package"},
            "--output json",
        ),
    ],
)
def test_show_basic_with_installed_packages_single(
    expected: str,
    output_format: str,
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.1.0"))

    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"

    installed.add_package(cachy_010)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": []},
            },
        }
    )

    tester.execute("cachy " + output_format if output_format else "cachy")

    if output_format:
        assert json.loads(tester.io.fetch_output()) == expected
    else:
        assert [
            line.strip() for line in tester.io.fetch_output().splitlines()
        ] == expected


@pytest.mark.parametrize(
    ("expected", "output_format"),
    [
        (
            [
                "name         : foo-bar",
                "version      : 0.1.0",
                "description  : Foobar package",
            ],
            "",
        ),
        (
            {"name": "foo-bar", "version": "0.1.0", "description": "Foobar package"},
            "--output json",
        ),
    ],
)
def test_show_basic_with_installed_packages_single_canonicalized(
    expected: str,
    output_format: str,
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("foo-bar", "^0.1.0"))

    foo_bar = get_package("foo-bar", "0.1.0")
    foo_bar.description = "Foobar package"

    installed.add_package(foo_bar)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo-bar",
                    "version": "0.1.0",
                    "description": "Foobar package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"foo-bar": []},
            },
        }
    )

    tester.execute("Foo_Bar " + output_format if output_format else "Foo_Bar")

    if output_format:
        assert json.loads(tester.io.fetch_output()) == expected
    else:
        assert [
            line.strip() for line in tester.io.fetch_output().splitlines()
        ] == expected


@pytest.mark.parametrize(
    ("expected", "output_format"),
    [
        (
            """\
cachy        0.1.0 Cachy package
pendulum (!) 2.0.0 Pendulum package
""",
            "",
        ),
        (
            [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "installed_status": "installed",
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "installed_status": "not-installed",
                },
            ],
            "--output json",
        ),
    ],
)
def test_show_basic_with_not_installed_packages_non_decorated(
    expected: str,
    output_format: str,
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.1.0"))
    poetry.package.add_dependency(Factory.create_dependency("pendulum", "^2.0.0"))

    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    installed.add_package(cachy_010)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": []},
            },
        }
    )

    tester.execute(output_format)

    if output_format:
        assert json.loads(tester.io.fetch_output()) == expected
    else:
        assert tester.io.fetch_output() == expected


def test_show_basic_with_not_installed_packages_decorated(
    tester: CommandTester, poetry: Poetry, installed: Repository
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.1.0"))
    poetry.package.add_dependency(Factory.create_dependency("pendulum", "^2.0.0"))

    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    installed.add_package(cachy_010)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": []},
            },
        }
    )

    tester.execute(decorated=True)

    expected = """\
\033[36mcachy   \033[39m \033[39;1m0.1.0\033[39;22m Cachy package
\033[31mpendulum\033[39m \033[39;1m2.0.0\033[39;22m Pendulum package
"""

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    ("expected", "output_format"),
    [
        (
            """\
cachy    0.1.0 0.2.0 Cachy package
pendulum 2.0.0 2.0.1 Pendulum package
""",
            "",
        ),
        (
            [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "latest_version": "0.2.0",
                    "description": "Cachy package",
                    "installed_status": "installed",
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "latest_version": "2.0.1",
                    "description": "Pendulum package",
                    "installed_status": "installed",
                },
            ],
            "--output json",
        ),
    ],
)
def test_show_latest_non_decorated(
    expected: str,
    output_format: str,
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.1.0"))
    poetry.package.add_dependency(Factory.create_dependency("pendulum", "^2.0.0"))

    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"
    cachy_020 = get_package("cachy", "0.2.0")
    cachy_020.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"
    pendulum_201 = get_package("pendulum", "2.0.1")
    pendulum_201.description = "Pendulum package"

    installed.add_package(cachy_010)
    installed.add_package(pendulum_200)

    repo.add_package(cachy_010)
    repo.add_package(cachy_020)
    repo.add_package(pendulum_200)
    repo.add_package(pendulum_201)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": []},
            },
        }
    )

    tester.execute("--latest" if not output_format else "--latest " + output_format)

    if output_format:
        assert json.loads(tester.io.fetch_output()) == expected
    else:
        assert tester.io.fetch_output() == expected


def test_show_latest_decorated(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.1.0"))
    poetry.package.add_dependency(Factory.create_dependency("pendulum", "^2.0.0"))

    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"
    cachy_020 = get_package("cachy", "0.2.0")
    cachy_020.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"
    pendulum_201 = get_package("pendulum", "2.0.1")
    pendulum_201.description = "Pendulum package"

    installed.add_package(cachy_010)
    installed.add_package(pendulum_200)

    repo.add_package(cachy_010)
    repo.add_package(cachy_020)
    repo.add_package(pendulum_200)
    repo.add_package(pendulum_201)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": []},
            },
        }
    )

    tester.execute("--latest", decorated=True)

    expected = """\
\033[36mcachy   \033[39m \033[39;1m0.1.0\033[39;22m\
 \033[33m0.2.0\033[39m Cachy package
\033[36mpendulum\033[39m \033[39;1m2.0.0\033[39;22m\
 \033[31m2.0.1\033[39m Pendulum package
"""

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    ("expected", "output_format"),
    [
        (
            """\
cachy 0.1.0 0.2.0 Cachy package
""",
            "",
        ),
        (
            [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "latest_version": "0.2.0",
                    "description": "Cachy package",
                    "installed_status": "installed",
                },
            ],
            "--output json",
        ),
    ],
)
def test_show_outdated(
    expected: str,
    output_format: str,
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.1.0"))
    poetry.package.add_dependency(Factory.create_dependency("pendulum", "^2.0.0"))

    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"
    cachy_020 = get_package("cachy", "0.2.0")
    cachy_020.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    installed.add_package(cachy_010)
    installed.add_package(pendulum_200)

    repo.add_package(cachy_010)
    repo.add_package(cachy_020)
    repo.add_package(pendulum_200)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": []},
            },
        }
    )

    tester.execute("--outdated" if not output_format else "--outdated " + output_format)

    if output_format:
        assert json.loads(tester.io.fetch_output()) == expected
    else:
        assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    ("expected", "output_format"),
    [
        (
            "",
            "",
        ),
        (
            [],
            "--output json",
        ),
    ],
)
def test_show_outdated_with_only_up_to_date_packages(
    expected: str,
    output_format: str,
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
) -> None:
    cachy_020 = get_package("cachy", "0.2.0")
    cachy_020.description = "Cachy package"

    installed.add_package(cachy_020)
    repo.add_package(cachy_020)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.2.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": []},
            },
        }
    )

    tester.execute("--outdated" if not output_format else "--outdated " + output_format)

    if output_format:
        assert json.loads(tester.io.fetch_output()) == expected
    else:
        assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    ("expected", "output_format"),
    [
        (
            """\
cachy 0.1.0 0.2.0 Cachy package
""",
            "",
        ),
        (
            [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "latest_version": "0.2.0",
                    "description": "Cachy package",
                    "installed_status": "installed",
                },
            ],
            "--output json",
        ),
    ],
)
def test_show_outdated_has_prerelease_but_not_allowed(
    expected: str,
    output_format: str,
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.1.0"))
    poetry.package.add_dependency(Factory.create_dependency("pendulum", "^2.0.0"))

    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"
    cachy_020 = get_package("cachy", "0.2.0")
    cachy_020.description = "Cachy package"
    cachy_030dev = get_package("cachy", "0.3.0.dev123")
    cachy_030dev.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    installed.add_package(cachy_010)
    installed.add_package(pendulum_200)

    # sorting isn't used, so this has to be the first element to
    # replicate the issue in PR #1548
    repo.add_package(cachy_030dev)
    repo.add_package(cachy_010)
    repo.add_package(cachy_020)
    repo.add_package(pendulum_200)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": []},
            },
        }
    )

    tester.execute("--outdated" if not output_format else "--outdated " + output_format)

    if output_format:
        assert json.loads(tester.io.fetch_output()) == expected
    else:
        assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    ("expected", "output_format"),
    [
        (
            """\
cachy 0.1.0.dev1 0.3.0.dev123 Cachy package
""",
            "",
        ),
        (
            [
                {
                    "name": "cachy",
                    "version": "0.1.0.dev1",
                    "latest_version": "0.3.0.dev123",
                    "description": "Cachy package",
                    "installed_status": "installed",
                },
            ],
            "--output json",
        ),
    ],
)
def test_show_outdated_has_prerelease_and_allowed(
    expected: str,
    output_format: str,
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
) -> None:
    poetry.package.add_dependency(
        Factory.create_dependency(
            "cachy", {"version": ">=0.0.1", "allow-prereleases": True}
        )
    )
    poetry.package.add_dependency(Factory.create_dependency("pendulum", "^2.0.0"))

    cachy_010dev = get_package("cachy", "0.1.0.dev1")
    cachy_010dev.description = "Cachy package"
    cachy_020 = get_package("cachy", "0.2.0")
    cachy_020.description = "Cachy package"
    cachy_030dev = get_package("cachy", "0.3.0.dev123")
    cachy_030dev.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    installed.add_package(cachy_010dev)
    installed.add_package(pendulum_200)

    # sorting isn't used, so this has to be the first element to
    # replicate the issue in PR #1548
    repo.add_package(cachy_030dev)
    repo.add_package(cachy_010dev)
    repo.add_package(cachy_020)
    repo.add_package(pendulum_200)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0.dev1",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": []},
            },
        }
    )

    tester.execute("--outdated" if not output_format else "--outdated " + output_format)

    if output_format:
        assert json.loads(tester.io.fetch_output()) == expected
    else:
        assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    ("expected", "output_format"),
    [
        (
            """\
cachy    0.1.0 0.2.0 Cachy package
pendulum 2.0.0 2.0.1 Pendulum package
""",
            "",
        ),
        (
            [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "latest_version": "0.2.0",
                    "description": "Cachy package",
                    "installed_status": "installed",
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "latest_version": "2.0.1",
                    "description": "Pendulum package",
                    "installed_status": "installed",
                },
            ],
            "--output json",
        ),
    ],
)
def test_show_outdated_formatting(
    expected: str,
    output_format: str,
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.1.0"))
    poetry.package.add_dependency(Factory.create_dependency("pendulum", "^2.0.0"))

    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"
    cachy_020 = get_package("cachy", "0.2.0")
    cachy_020.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"
    pendulum_201 = get_package("pendulum", "2.0.1")
    pendulum_201.description = "Pendulum package"

    installed.add_package(cachy_010)
    installed.add_package(pendulum_200)

    repo.add_package(cachy_010)
    repo.add_package(cachy_020)
    repo.add_package(pendulum_200)
    repo.add_package(pendulum_201)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": []},
            },
        }
    )

    tester.execute("--outdated" if not output_format else "--outdated " + output_format)

    if output_format:
        assert json.loads(tester.io.fetch_output()) == expected
    else:
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
) -> None:
    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"
    cachy_020 = get_package("cachy", "0.2.0")
    cachy_020.description = "Cachy package"
    cachy_030 = get_package("cachy", "0.3.0")
    cachy_030.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    demo_010 = get_package("demo", "0.1.0")
    demo_010.description = ""

    my_package_011 = get_package("project-with-setup", "0.1.1")
    my_package_011.description = "Demo project."

    installed.add_package(cachy_020)
    installed.add_package(pendulum_200)
    installed.add_package(demo_010)
    installed.add_package(my_package_011)

    repo.add_package(cachy_020)
    repo.add_package(cachy_030)
    repo.add_package(pendulum_200)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.2.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "demo",
                    "version": "0.1.0",
                    "description": "Demo package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "source": {
                        "type": "file",
                        "reference": "",
                        "url": "../distributions/demo-0.1.0-py2.py3-none-any.whl",
                    },
                },
                {
                    "name": "project-with-setup",
                    "version": "0.1.1",
                    "description": "Demo project.",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "dependencies": {
                        "pendulum": ">=1.4.4",
                        "cachy": {"version": ">=0.2.0", "extras": ["msgpack"]},
                    },
                    "source": {
                        "type": "directory",
                        "reference": "",
                        "url": "../project_with_setup",
                    },
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {
                    "cachy": [],
                    "pendulum": [],
                    "demo": [],
                    "project-with-setup": [],
                },
            },
        }
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
def test_show_outdated_git_dev_dependency(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
) -> None:
    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"
    cachy_020 = get_package("cachy", "0.2.0")
    cachy_020.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    demo_011 = get_package("demo", "0.1.1")
    demo_011.description = "Demo package"

    pytest = get_package("pytest", "3.4.3")
    pytest.description = "Pytest"

    installed.add_package(cachy_010)
    installed.add_package(pendulum_200)
    installed.add_package(demo_011)
    installed.add_package(pytest)

    repo.add_package(cachy_010)
    repo.add_package(cachy_020)
    repo.add_package(pendulum_200)
    repo.add_package(pytest)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "demo",
                    "version": "0.1.1",
                    "description": "Demo package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "source": {
                        "type": "git",
                        "reference": MOCK_DEFAULT_GIT_REVISION,
                        "resolved_reference": MOCK_DEFAULT_GIT_REVISION,
                        "url": "https://github.com/demo/demo.git",
                    },
                },
                {
                    "name": "pytest",
                    "version": "3.4.3",
                    "description": "Pytest",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": [], "demo": [], "pytest": []},
            },
        }
    )

    tester.execute("--outdated")

    expected = """\
cachy 0.1.0         0.2.0         Cachy package
demo  0.1.1 9cf87a2 0.1.2 9cf87a2 Demo package
"""

    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize("project_directory", ["project_with_git_dev_dependency"])
def test_show_outdated_no_dev_git_dev_dependency(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
) -> None:
    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"
    cachy_020 = get_package("cachy", "0.2.0")
    cachy_020.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    demo_011 = get_package("demo", "0.1.1")
    demo_011.description = "Demo package"

    pytest = get_package("pytest", "3.4.3")
    pytest.description = "Pytest"

    installed.add_package(cachy_010)
    installed.add_package(pendulum_200)
    installed.add_package(demo_011)
    installed.add_package(pytest)

    repo.add_package(cachy_010)
    repo.add_package(cachy_020)
    repo.add_package(pendulum_200)
    repo.add_package(pytest)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "demo",
                    "version": "0.1.1",
                    "description": "Demo package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "source": {
                        "type": "git",
                        "reference": MOCK_DEFAULT_GIT_REVISION,
                        "url": "https://github.com/demo/pyproject-demo.git",
                    },
                },
                {
                    "name": "pytest",
                    "version": "3.4.3",
                    "description": "Pytest",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": [], "demo": [], "pytest": []},
            },
        }
    )

    tester.execute("--outdated --without dev")

    expected = """\
cachy 0.1.0 0.2.0 Cachy package
"""

    assert tester.io.fetch_output() == expected


def test_show_hides_incompatible_package(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
) -> None:
    poetry.package.add_dependency(
        Factory.create_dependency("cachy", {"version": "^0.1.0", "python": "< 2.0"})
    )
    poetry.package.add_dependency(Factory.create_dependency("pendulum", "^2.0.0"))

    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    installed.add_package(pendulum_200)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": []},
            },
        }
    )

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
) -> None:
    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    installed.add_package(pendulum_200)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "requirements": {"python": "1.0"},
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": []},
            },
        }
    )

    tester.execute("--all")

    expected = """\
cachy     0.1.0 Cachy package
pendulum  2.0.0 Pendulum package
"""

    assert tester.io.fetch_output() == expected


def test_show_hides_incompatible_package_with_duplicate(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
) -> None:
    poetry.package.add_dependency(
        Factory.create_dependency("cachy", {"version": "0.1.0", "platform": "linux"})
    )
    poetry.package.add_dependency(
        Factory.create_dependency("cachy", {"version": "0.1.1", "platform": "darwin"})
    )

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "files": [],
                },
                {
                    "name": "cachy",
                    "version": "0.1.1",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "files": [],
                },
            ],
            "metadata": {"content-hash": "123456789"},
        }
    )

    tester.execute()

    expected = """\
cachy (!) 0.1.1 Cachy package
"""

    assert tester.io.fetch_output() == expected


def test_show_all_shows_all_duplicates(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
) -> None:
    poetry.package.add_dependency(
        Factory.create_dependency("cachy", {"version": "0.1.0", "platform": "linux"})
    )
    poetry.package.add_dependency(
        Factory.create_dependency("cachy", {"version": "0.1.1", "platform": "darwin"})
    )

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "files": [],
                },
                {
                    "name": "cachy",
                    "version": "0.1.1",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "files": [],
                },
            ],
            "metadata": {"content-hash": "123456789"},
        }
    )

    tester.execute("--all")

    expected = """\
cachy     0.1.0 Cachy package
cachy (!) 0.1.1 Cachy package
"""

    assert tester.io.fetch_output() == expected


def test_show_non_dev_with_basic_installed_packages(
    tester: CommandTester, poetry: Poetry, installed: Repository
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.1.0"))
    poetry.package.add_dependency(Factory.create_dependency("pendulum", "^2.0.0"))
    poetry.package.add_dependency(
        Factory.create_dependency("pytest", "*", groups=["dev"])
    )

    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    pytest_373 = get_package("pytest", "3.7.3")
    pytest_373.description = "Pytest package"

    installed.add_package(cachy_010)
    installed.add_package(pendulum_200)
    installed.add_package(pytest_373)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pytest",
                    "version": "3.7.3",
                    "description": "Pytest package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": [], "pytest": []},
            },
        }
    )

    tester.execute("--without dev")

    expected = """\
cachy    0.1.0 Cachy package
pendulum 2.0.0 Pendulum package
"""

    assert tester.io.fetch_output() == expected


def test_show_with_group_only(
    tester: CommandTester, poetry: Poetry, installed: Repository
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.1.0"))
    poetry.package.add_dependency(Factory.create_dependency("pendulum", "^2.0.0"))
    poetry.package.add_dependency(
        Factory.create_dependency("pytest", "*", groups=["dev"])
    )

    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    pytest_373 = get_package("pytest", "3.7.3")
    pytest_373.description = "Pytest package"

    installed.add_package(cachy_010)
    installed.add_package(pendulum_200)
    installed.add_package(pytest_373)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pytest",
                    "version": "3.7.3",
                    "description": "Pytest package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": [], "pytest": []},
            },
        }
    )

    tester.execute("--only dev")

    expected = """\
pytest 3.7.3 Pytest package
"""

    assert tester.io.fetch_output() == expected


def test_show_with_optional_group(
    tester: CommandTester, poetry: Poetry, installed: Repository
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.1.0"))
    poetry.package.add_dependency(Factory.create_dependency("pendulum", "^2.0.0"))
    group = DependencyGroup("dev", optional=True)
    group.add_dependency(Factory.create_dependency("pytest", "*", groups=["dev"]))
    poetry.package.add_dependency_group(group)

    cachy_010 = get_package("cachy", "0.1.0")
    cachy_010.description = "Cachy package"

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"

    pytest_373 = get_package("pytest", "3.7.3")
    pytest_373.description = "Pytest package"

    installed.add_package(cachy_010)
    installed.add_package(pendulum_200)
    installed.add_package(pytest_373)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.1.0",
                    "description": "Cachy package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pytest",
                    "version": "3.7.3",
                    "description": "Pytest package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": [], "pytest": []},
            },
        }
    )

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


def test_show_tree(
    tester: CommandTester, poetry: Poetry, installed: Repository
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.2.0"))

    cachy2 = get_package("cachy", "0.2.0")
    cachy2.add_dependency(Factory.create_dependency("msgpack-python", ">=0.5 <0.6"))

    installed.add_package(cachy2)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.2.0",
                    "description": "",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "dependencies": {"msgpack-python": ">=0.5 <0.6"},
                },
                {
                    "name": "msgpack-python",
                    "version": "0.5.1",
                    "description": "",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "msgpack-python": []},
            },
        }
    )

    tester.execute("--tree", supports_utf8=False)

    expected = """\
cachy 0.2.0
`-- msgpack-python >=0.5 <0.6
"""

    assert tester.io.fetch_output() == expected


def test_show_tree_no_dev(
    tester: CommandTester, poetry: Poetry, installed: Repository
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.2.0"))
    poetry.package.add_dependency(
        Factory.create_dependency("pytest", "^6.1.0", groups=["dev"])
    )

    cachy2 = get_package("cachy", "0.2.0")
    cachy2.add_dependency(Factory.create_dependency("msgpack-python", ">=0.5 <0.6"))
    installed.add_package(cachy2)

    pytest = get_package("pytest", "6.1.1")
    installed.add_package(pytest)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.2.0",
                    "description": "",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "dependencies": {"msgpack-python": ">=0.5 <0.6"},
                },
                {
                    "name": "msgpack-python",
                    "version": "0.5.1",
                    "description": "",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "pytest",
                    "version": "6.1.1",
                    "description": "",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "msgpack-python": [], "pytest": []},
            },
        }
    )

    tester.execute("--tree --without dev")

    expected = """\
cachy 0.2.0
└── msgpack-python >=0.5 <0.6
"""

    assert tester.io.fetch_output() == expected


def test_show_tree_why_package(
    tester: CommandTester, poetry: Poetry, installed: Repository
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("a", "=0.0.1"))

    a = get_package("a", "0.0.1")
    installed.add_package(a)
    a.add_dependency(Factory.create_dependency("b", "=0.0.1"))

    b = get_package("b", "0.0.1")
    a.add_dependency(Factory.create_dependency("c", "=0.0.1"))
    installed.add_package(b)

    c = get_package("c", "0.0.1")
    installed.add_package(c)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "a",
                    "version": "0.0.1",
                    "dependencies": {"b": "=0.0.1"},
                    "python-versions": "*",
                    "optional": False,
                },
                {
                    "name": "b",
                    "version": "0.0.1",
                    "dependencies": {"c": "=0.0.1"},
                    "python-versions": "*",
                    "optional": False,
                },
                {
                    "name": "c",
                    "version": "0.0.1",
                    "python-versions": "*",
                    "optional": False,
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"a": [], "b": [], "c": []},
            },
        }
    )

    tester.execute("--tree --why b")

    expected = """\
a 0.0.1
└── b =0.0.1
    └── c =0.0.1 \n"""

    assert tester.io.fetch_output() == expected


def test_show_tree_why(
    tester: CommandTester, poetry: Poetry, installed: Repository
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("a", "=0.0.1"))

    a = get_package("a", "0.0.1")
    installed.add_package(a)
    a.add_dependency(Factory.create_dependency("b", "=0.0.1"))

    b = get_package("b", "0.0.1")
    a.add_dependency(Factory.create_dependency("c", "=0.0.1"))
    installed.add_package(b)

    c = get_package("c", "0.0.1")
    installed.add_package(c)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "a",
                    "version": "0.0.1",
                    "dependencies": {"b": "=0.0.1"},
                    "python-versions": "*",
                    "optional": False,
                },
                {
                    "name": "b",
                    "version": "0.0.1",
                    "dependencies": {"c": "=0.0.1"},
                    "python-versions": "*",
                    "optional": False,
                },
                {
                    "name": "c",
                    "version": "0.0.1",
                    "python-versions": "*",
                    "optional": False,
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"a": [], "b": [], "c": []},
            },
        }
    )

    tester.execute("--why")

    # this has to be on a single line due to the padding whitespace, which gets stripped
    # by pre-commit.
    expected = """a 0.0.1        \nb 0.0.1 from a \nc 0.0.1 from b \n"""

    assert tester.io.fetch_output() == expected


def test_show_required_by_deps(
    tester: CommandTester, poetry: Poetry, installed: Repository
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.2.0"))
    poetry.package.add_dependency(Factory.create_dependency("pendulum", "2.0.0"))

    cachy2 = get_package("cachy", "0.2.0")
    cachy2.add_dependency(Factory.create_dependency("msgpack-python", ">=0.5 <0.6"))

    pendulum = get_package("pendulum", "2.0.0")
    pendulum.add_dependency(Factory.create_dependency("CachY", "^0.2.0"))

    installed.add_package(cachy2)
    installed.add_package(pendulum)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.2.0",
                    "description": "",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "dependencies": {"msgpack-python": ">=0.5 <0.6"},
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "dependencies": {"cachy": ">=0.2.0 <0.3.0"},
                },
                {
                    "name": "msgpack-python",
                    "version": "0.5.1",
                    "description": "",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "pendulum": [], "msgpack-python": []},
            },
        }
    )

    tester.execute("cachy")

    expected = """\
 name         : cachy
 version      : 0.2.0
 description  :

dependencies
 - msgpack-python >=0.5 <0.6

required by
 - pendulum requires >=0.2.0 <0.3.0
""".splitlines()
    actual = [line.rstrip() for line in tester.io.fetch_output().splitlines()]
    assert actual == expected


@pytest.mark.parametrize("truncate", [False, True])
def test_show_entire_description_truncate(
    tester: CommandTester, poetry: Poetry, installed: Repository, truncate: str
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.2.0"))

    cachy2 = get_package("cachy", "0.2.0")
    cachy2.add_dependency(Factory.create_dependency("msgpack-python", ">=0.5 <0.6"))

    installed.add_package(cachy2)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.2.0",
                    "description": "This is a veeeeeeeery long description that might be truncated.",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "dependencies": {"msgpack-python": ">=0.5 <0.6"},
                },
                {
                    "name": "msgpack-python",
                    "version": "0.5.1",
                    "description": "",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "msgpack-python": []},
            },
        }
    )

    tester.execute("" if truncate else "--no-truncate")

    if truncate:
        expected = """\
cachy              0.2.0 This is a veeeeeeeery long description that might ...
msgpack-python (!) 0.5.1"""
    else:
        expected = """\
cachy              0.2.0 This is a veeeeeeeery long description that might be truncated.
msgpack-python (!) 0.5.1"""

    assert tester.io.fetch_output().strip() == expected


def test_show_errors_without_lock_file(tester: CommandTester, poetry: Poetry) -> None:
    assert not poetry.locker.lock.exists()

    tester.execute()

    expected = "Error: poetry.lock not found. Run `poetry lock` to create it.\n"
    assert tester.io.fetch_error() == expected
    assert tester.status_code == 1


def test_show_dependency_installed_from_git_in_dev(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
) -> None:
    # Add a regular dependency for a package in main, and a git dependency for the same
    # package in dev.
    poetry.package.add_dependency(Factory.create_dependency("demo", "^0.1.1"))
    poetry.package.add_dependency(
        Factory.create_dependency(
            "demo", {"git": "https://github.com/demo/demo.git"}, groups=["dev"]
        )
    )

    demo_011 = get_package("demo", "0.1.1")
    demo_011.description = "Demo package"
    repo.add_package(demo_011)

    pendulum_200 = get_package("pendulum", "2.0.0")
    pendulum_200.description = "Pendulum package"
    repo.add_package(pendulum_200)

    # The git package is the one that gets into the lockfile.
    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "demo",
                    "version": "0.1.2",
                    "description": "Demo package",
                    "optional": False,
                    "python-versions": "*",
                    "develop": False,
                    "source": {
                        "type": "git",
                        "reference": MOCK_DEFAULT_GIT_REVISION,
                        "resolved_reference": MOCK_DEFAULT_GIT_REVISION,
                        "url": "https://github.com/demo/demo.git",
                    },
                },
                {
                    "name": "pendulum",
                    "version": "2.0.0",
                    "description": "Pendulum package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"demo": [], "pendulum": []},
            },
        }
    )

    # Nothing needs updating, there is no confusion between the git and not-git
    # packages.
    tester.execute("--outdated")
    assert tester.io.fetch_output() == ""


def test_url_dependency_is_not_outdated_by_repository_package(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
) -> None:
    demo_url = (
        "https://files.pythonhosted.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
    )
    poetry.package.add_dependency(
        Factory.create_dependency(
            "demo",
            {"url": demo_url},
        )
    )

    # A newer version of demo is available in the repository.
    demo_100 = get_package("demo", "1.0.0")
    repo.add_package(demo_100)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "demo",
                    "version": "0.1.0",
                    "description": "Demo package",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "source": {
                        "type": "url",
                        "url": demo_url,
                    },
                }
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "hashes": {"demo": []},
            },
        }
    )

    # The url dependency on demo is not made outdated by the existence of a newer
    # version in the repository.
    tester.execute("--outdated")
    assert tester.io.fetch_output() == ""


def test_show_top_level(
    tester: CommandTester, poetry: Poetry, installed: Repository
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("cachy", "^0.2.0"))

    cachy2 = get_package("cachy", "0.2.0")
    cachy2.add_dependency(Factory.create_dependency("msgpack-python", ">=0.5 <0.6"))

    installed.add_package(cachy2)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "cachy",
                    "version": "0.2.0",
                    "description": "",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "dependencies": {"msgpack-python": ">=0.5 <0.6"},
                },
                {
                    "name": "msgpack-python",
                    "version": "0.5.1",
                    "description": "",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"cachy": [], "msgpack-python": []},
            },
        }
    )

    tester.execute("--top-level")

    expected = """cachy              0.2.0 \n"""

    assert tester.io.fetch_output() == expected


def test_show_top_level_with_explicitly_defined_dependency(
    tester: CommandTester, poetry: Poetry, installed: Repository
) -> None:
    poetry.package.add_dependency(Factory.create_dependency("a", "^0.1.0"))
    poetry.package.add_dependency(Factory.create_dependency("b", "^0.2.0"))

    a = get_package("a", "0.1.0")
    a.add_dependency(Factory.create_dependency("b", "0.2.0"))
    b = get_package("b", "0.2.0")

    installed.add_package(a)
    installed.add_package(b)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "a",
                    "version": "0.1.0",
                    "description": "",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "dependencies": {"b": "0.2.0"},
                },
                {
                    "name": "b",
                    "version": "0.2.0",
                    "description": "",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"a": [], "b": []},
            },
        }
    )

    tester.execute("--top-level")

    expected = """a 0.1.0 \nb 0.2.0 \n"""

    assert tester.io.fetch_output() == expected


def test_show_top_level_with_extras(
    tester: CommandTester, poetry: Poetry, installed: Repository
) -> None:
    black_dep = Factory.create_dependency(
        "black", {"version": "23.3.0", "extras": ["d"]}
    )
    poetry.package.add_dependency(black_dep)

    black_package = get_package("black", "23.3.0")
    black_package.add_dependency(
        Factory.create_dependency(
            "aiohttp",
            {
                "version": ">=3.7.4",
                "optional": True,
                "markers": 'extra == "d"',
            },
        )
    )
    installed.add_package(black_package)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "black",
                    "version": "23.3.0",
                    "description": "",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "dependencies": {
                        "aiohttp": {
                            "version": ">=3.7.4",
                            "optional": True,
                            "markers": 'extra == "d"',
                        }
                    },
                },
                {
                    "name": "aiohttp",
                    "version": "3.8.4",
                    "description": "",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"black": [], "aiohttp": []},
            },
        }
    )

    tester.execute("--top-level")

    expected = """black 23.3.0 \n"""

    assert tester.io.fetch_output() == expected


def test_show_error_top_level_with_tree(tester: CommandTester) -> None:
    expected = "Error: Cannot use --tree and --top-level at the same time.\n"
    tester.execute("--top-level --tree")
    assert tester.io.fetch_error() == expected
    assert tester.status_code == 1


def test_show_error_top_level_with_single_package(tester: CommandTester) -> None:
    expected = "Error: Cannot use --top-level when displaying a single package.\n"
    tester.execute("--top-level some_package_name")
    assert tester.io.fetch_error() == expected
    assert tester.status_code == 1


@pytest.mark.parametrize(
    ("project_directory", "required_fixtures"),
    [
        (
            "deleted_directory_dependency",
            [],
        ),
    ],
)
def test_show_outdated_missing_directory_dependency(
    tester: CommandTester,
    poetry: Poetry,
    installed: Repository,
    repo: TestRepository,
) -> None:
    with (poetry.pyproject.file.path.parent / "poetry.lock").open(mode="rb") as f:
        data = tomllib.load(f)

    assert isinstance(poetry.locker, TestLocker)
    poetry.locker.mock_lock_data(data)

    poetry.package.add_dependency(
        Factory.create_dependency(
            "missing",
            {"path": data["package"][0]["source"]["url"]},
        )
    )

    with pytest.raises(ValueError, match="does not exist"):
        tester.execute("")


def test_show_error_invalid_output_format(
    tester: CommandTester,
) -> None:
    expected = "Error: Invalid output format. Supported formats are: json, text.\n"
    tester.execute("--output invalid")
    assert tester.io.fetch_error() == expected
    assert tester.status_code == 1


def test_show_error_invalid_output_format_with_tree_option(
    tester: CommandTester,
) -> None:
    expected = "Error: --tree option can only be used the the text output.\n"
    tester.execute("--output json --tree")
    assert tester.io.fetch_error() == expected
    assert tester.status_code == 1
