from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from collections.abc import Mapping

import pytest

from poetry.core.packages.package import Package

from poetry.console.commands.add import AddCommand
from poetry.console.commands.self.self_command import SelfCommand
from poetry.factory import Factory
from tests.console.commands.self.utils import get_self_command_dependencies


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("self add")


def assert_plugin_add_result(
    tester: CommandTester,
    expected: str,
    constraint: str | Mapping[str, str | list[str]],
) -> None:
    assert tester.io.fetch_output() == expected
    dependencies: dict[str, Any] = get_self_command_dependencies()

    assert "poetry-plugin" in dependencies
    assert dependencies["poetry-plugin"] == constraint


def test_add_no_constraint(
    tester: CommandTester,
    repo: TestRepository,
) -> None:
    repo.add_package(Package("poetry-plugin", "0.1.0"))

    tester.execute("poetry-plugin")

    expected = """\
Using version ^0.1.0 for poetry-plugin

Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing poetry-plugin (0.1.0)

Writing lock file
"""
    assert_plugin_add_result(tester, expected, "^0.1.0")


def test_add_with_constraint(
    tester: CommandTester,
    repo: TestRepository,
) -> None:
    repo.add_package(Package("poetry-plugin", "0.1.0"))
    repo.add_package(Package("poetry-plugin", "0.2.0"))

    tester.execute("poetry-plugin@^0.2.0")

    expected = """
Updating dependencies
Resolving dependencies...

Package operations: 1 install, 0 updates, 0 removals

  - Installing poetry-plugin (0.2.0)

Writing lock file
"""

    assert_plugin_add_result(tester, expected, "^0.2.0")


def test_add_with_git_constraint(
    tester: CommandTester,
    repo: TestRepository,
) -> None:
    repo.add_package(Package("pendulum", "2.0.5"))

    tester.execute("git+https://github.com/demo/poetry-plugin.git")

    expected = """
Updating dependencies
Resolving dependencies...

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (2.0.5)
  - Installing poetry-plugin (0.1.2 9cf87a2)

Writing lock file
"""

    assert_plugin_add_result(
        tester, expected, {"git": "https://github.com/demo/poetry-plugin.git"}
    )


def test_add_with_git_constraint_with_extras(
    tester: CommandTester,
    repo: TestRepository,
) -> None:
    repo.add_package(Package("pendulum", "2.0.5"))
    repo.add_package(Package("tomlkit", "0.7.0"))

    tester.execute("git+https://github.com/demo/poetry-plugin.git[foo]")

    expected = """
Updating dependencies
Resolving dependencies...

Package operations: 3 installs, 0 updates, 0 removals

  - Installing pendulum (2.0.5)
  - Installing tomlkit (0.7.0)
  - Installing poetry-plugin (0.1.2 9cf87a2)

Writing lock file
"""

    constraint: dict[str, str | list[str]] = {
        "git": "https://github.com/demo/poetry-plugin.git",
        "extras": ["foo"],
    }
    assert_plugin_add_result(tester, expected, constraint)


@pytest.mark.parametrize(
    "url, rev",
    [
        ("git+https://github.com/demo/poetry-plugin2.git#subdirectory=subdir", None),
        (
            "git+https://github.com/demo/poetry-plugin2.git@master#subdirectory=subdir",
            "master",
        ),
    ],
)
def test_add_with_git_constraint_with_subdirectory(
    url: str,
    rev: str | None,
    tester: CommandTester,
    repo: TestRepository,
) -> None:
    repo.add_package(Package("pendulum", "2.0.5"))

    tester.execute(url)

    expected = """
Updating dependencies
Resolving dependencies...

Package operations: 2 installs, 0 updates, 0 removals

  - Installing pendulum (2.0.5)
  - Installing poetry-plugin (0.1.2 9cf87a2)

Writing lock file
"""

    constraint = {
        "git": "https://github.com/demo/poetry-plugin2.git",
        "subdirectory": "subdir",
    }

    if rev:
        constraint["rev"] = rev

    assert_plugin_add_result(
        tester,
        expected,
        constraint,
    )


def test_add_existing_plugin_warns_about_no_operation(
    tester: CommandTester,
    repo: TestRepository,
    installed: TestRepository,
) -> None:
    pyproject = SelfCommand.get_default_system_pyproject_file()
    with open(pyproject, "w", encoding="utf-8", newline="") as f:
        f.write(
            f"""\
[tool.poetry]
name = "poetry-instance"
version = "1.2.0"
description = "Python dependency management and packaging made easy."
authors = []

[tool.poetry.dependencies]
python = "^3.6"

[tool.poetry.group.{SelfCommand.ADDITIONAL_PACKAGE_GROUP}.dependencies]
poetry-plugin = "^1.2.3"
"""
        )

    installed.add_package(Package("poetry-plugin", "1.2.3"))

    repo.add_package(Package("poetry-plugin", "1.2.3"))

    tester.execute("poetry-plugin")

    assert isinstance(tester.command, AddCommand)
    expected = f"""\
The following packages are already present in the pyproject.toml and will be\
 skipped:

  - poetry-plugin
{tester.command._hint_update_packages}
Nothing to add.
"""

    assert tester.io.fetch_output() == expected


def test_add_existing_plugin_updates_if_requested(
    tester: CommandTester,
    repo: TestRepository,
    installed: TestRepository,
) -> None:
    pyproject = SelfCommand.get_default_system_pyproject_file()
    with open(pyproject, "w", encoding="utf-8", newline="") as f:
        f.write(
            f"""\
[tool.poetry]
name = "poetry-instance"
version = "1.2.0"
description = "Python dependency management and packaging made easy."
authors = []

[tool.poetry.dependencies]
python = "^3.6"

[tool.poetry.group.{SelfCommand.ADDITIONAL_PACKAGE_GROUP}.dependencies]
poetry-plugin = "^1.2.3"
"""
        )

    installed.add_package(Package("poetry-plugin", "1.2.3"))

    repo.add_package(Package("poetry-plugin", "1.2.3"))
    repo.add_package(Package("poetry-plugin", "2.3.4"))

    tester.execute("poetry-plugin@latest")

    expected = """\
Using version ^2.3.4 for poetry-plugin

Updating dependencies
Resolving dependencies...

Package operations: 0 installs, 1 update, 0 removals

  - Updating poetry-plugin (1.2.3 -> 2.3.4)

Writing lock file
"""

    assert_plugin_add_result(tester, expected, "^2.3.4")


def test_adding_a_plugin_can_update_poetry_dependencies_if_needed(
    tester: CommandTester,
    repo: TestRepository,
    installed: TestRepository,
) -> None:
    poetry_package = Package("poetry", "1.2.0")
    poetry_package.add_dependency(Factory.create_dependency("tomlkit", "^0.7.0"))

    plugin_package = Package("poetry-plugin", "1.2.3")
    plugin_package.add_dependency(Factory.create_dependency("tomlkit", "^0.7.2"))

    installed.add_package(poetry_package)
    installed.add_package(Package("tomlkit", "0.7.1"))

    repo.add_package(plugin_package)
    repo.add_package(Package("tomlkit", "0.7.1"))
    repo.add_package(Package("tomlkit", "0.7.2"))

    tester.execute("poetry-plugin")

    expected = """\
Using version ^1.2.3 for poetry-plugin

Updating dependencies
Resolving dependencies...

Package operations: 1 install, 1 update, 0 removals

  - Updating tomlkit (0.7.1 -> 0.7.2)
  - Installing poetry-plugin (1.2.3)

Writing lock file
"""

    assert_plugin_add_result(tester, expected, "^1.2.3")
