from typing import TYPE_CHECKING
from typing import Dict
from typing import Union

import pytest
import tomlkit

from entrypoints import Distribution
from entrypoints import EntryPoint

from poetry.console.commands.plugin.plugin_command_mixin import PluginCommandMixin
from poetry.core.packages.package import Package

from poetry.factory import Factory
from poetry.repositories.installed_repository import InstalledRepository


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.console.commands.update import UpdateCommand
    from poetry.repositories import Repository
    from poetry.utils.env import MockEnv
    from tests.helpers import PoetryTestApplication
    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory


@pytest.fixture(autouse=True)
def setup(
    mocker: "MockerFixture", installed: "InstalledRepository", repo: "TestRepository"
):
    mocker.patch.object(InstalledRepository, "load", return_value=installed)
    mocker.patch.object(PluginCommandMixin, "get_plugin_entry_points", return_value=[])
    repo.add_package(installed.packages[0])


@pytest.fixture()
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
    return command_tester_factory("plugin add")


def assert_plugin_add_result(
    tester: "CommandTester",
    env: "MockEnv",
    expected: str,
    constraint: Union[str, Dict[str, str]],
):
    assert tester.io.fetch_output() == expected

    content = tomlkit.loads(
        env.path.joinpath("plugins.toml").read_text(encoding="utf-8")
    )
    assert "poetry-plugin" in content
    assert content["poetry-plugin"] == constraint


def test_add_no_constraint(
    app: "PoetryTestApplication", repo: "TestRepository", tester: "CommandTester"
):
    package = Package("poetry-plugin", "0.1.0")
    repo.add_package(package)

    tester.execute("poetry-plugin")

    expected = """\
Using version ^0.1.0 for poetry-plugin
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing poetry-plugin (0.1.0)
"""
    assert tester.io.fetch_output() == expected


def test_add_with_constraint(
    app: "PoetryTestApplication",
    repo: "TestRepository",
    tester: "CommandTester",
    env: "MockEnv",
    installed: "Repository",
):
    repo.add_package(Package("poetry-plugin", "0.1.0"))
    repo.add_package(Package("poetry-plugin", "0.2.0"))

    tester.execute("poetry-plugin@^0.2.0")

    expected = """\
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 1 install, 0 updates, 0 removals

  • Installing poetry-plugin (0.2.0)
"""

    assert_plugin_add_result(tester, env, expected, "^0.2.0")


def test_add_with_git_constraint(
    app: "PoetryTestApplication",
    repo: "TestRepository",
    tester: "CommandTester",
    env: "MockEnv",
    installed: "Repository",
):
    repo.add_package(Package("pendulum", "2.0.5"))

    tester.execute("git+https://github.com/demo/poetry-plugin.git")

    expected = """\
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 2 installs, 0 updates, 0 removals

  • Installing pendulum (2.0.5)
  • Installing poetry-plugin (0.1.2 9cf87a2)
"""

    assert_plugin_add_result(
        tester, env, expected, {"git": "https://github.com/demo/poetry-plugin.git"}
    )


def test_add_with_git_constraint_with_extras(
    app: "PoetryTestApplication",
    repo: "TestRepository",
    tester: "CommandTester",
    env: "MockEnv",
):
    repo.add_package(Package("pendulum", "2.0.5"))
    repo.add_package(Package("tomlkit", "0.7.0"))

    tester.execute("git+https://github.com/demo/poetry-plugin.git[foo]")

    expected = """\
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 3 installs, 0 updates, 0 removals

  • Installing pendulum (2.0.5)
  • Installing tomlkit (0.7.0)
  • Installing poetry-plugin (0.1.2 9cf87a2)
"""

    assert_plugin_add_result(
        tester,
        env,
        expected,
        {
            "git": "https://github.com/demo/poetry-plugin.git",
            "extras": ["foo"],
        },
    )


def test_add_existing_plugin_warns_about_no_operation(
    app: "PoetryTestApplication",
    repo: "TestRepository",
    tester: "CommandTester",
    env: "MockEnv",
    installed: "Repository",
    mocker: "MockerFixture",
):
    env.path.joinpath("plugins.toml").write_text(
        """\
poetry-plugin = "^1.2.3"
""",
        encoding="utf-8",
    )

    installed.add_package(Package("poetry-plugin", "1.2.3"))
    mocker.patch.object(
        PluginCommandMixin,
        "get_plugin_entry_points",
        return_value=[
            EntryPoint(
                "foo", "bar", "baz", distro=Distribution("poetry_plugin", "1.2.3")
            )
        ],
    )

    repo.add_package(Package("poetry-plugin", "1.2.3"))

    tester.execute("poetry-plugin")

    expected = """\
The following plugins are already present and will be skipped:

  • poetry-plugin

If you want to upgrade it to the latest compatible version, you can use `poetry plugin add plugin@latest.

"""

    assert tester.io.fetch_output() == expected

    update_command: "UpdateCommand" = app.find("update")
    # The update command should not have been called
    assert update_command.poetry.file.parent != env.path


def test_add_existing_plugin_updates_if_requested(
    app: "PoetryTestApplication",
    repo: "TestRepository",
    tester: "CommandTester",
    env: "MockEnv",
    installed: "Repository",
):
    env.path.joinpath("plugins.toml").write_text(
        """\
poetry-plugin = "^1.2.3"
""",
        encoding="utf-8",
    )

    installed.add_package(Package("poetry-plugin", "1.2.3"))

    repo.add_package(Package("poetry-plugin", "1.2.3"))
    repo.add_package(Package("poetry-plugin", "2.3.4"))

    tester.execute("poetry-plugin@latest")

    expected = """\
Using version ^2.3.4 for poetry-plugin
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 0 installs, 1 update, 0 removals

  • Updating poetry-plugin (1.2.3 -> 2.3.4)
"""

    assert_plugin_add_result(tester, env, expected, "^2.3.4")


def test_adding_a_plugin_can_update_poetry_dependencies_if_needed(
    app: "PoetryTestApplication",
    repo: "TestRepository",
    tester: "CommandTester",
    env: "MockEnv",
    installed: "Repository",
):
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

Writing lock file

Package operations: 1 install, 1 update, 0 removals

  • Updating tomlkit (0.7.1 -> 0.7.2)
  • Installing poetry-plugin (1.2.3)
"""

    assert_plugin_add_result(tester, env, expected, "^1.2.3")
