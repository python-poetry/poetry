from typing import TYPE_CHECKING

import pytest
import tomlkit

from entrypoints import Distribution
from entrypoints import EntryPoint
from poetry.core.packages.package import Package

from poetry.__version__ import __version__
from poetry.console.commands.plugin.plugin_command_mixin import PluginCommandMixin
from poetry.layouts.layout import POETRY_DEFAULT
from poetry.repositories.installed_repository import InstalledRepository


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.repositories import Repository
    from poetry.utils.env import MockEnv
    from tests.helpers import PoetryTestApplication
    from tests.types import CommandTesterFactory


@pytest.fixture(autouse=True)
def setup(mocker, installed, repo):
    mocker.patch.object(InstalledRepository, "load", return_value=installed)
    mocker.patch.object(PluginCommandMixin, "get_plugin_entry_points", return_value=[])
    repo.add_package(installed.packages[0])


@pytest.fixture()
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
    return command_tester_factory("plugin remove")


@pytest.fixture()
def pyproject(env: "MockEnv") -> None:
    pyproject = tomlkit.loads(POETRY_DEFAULT)
    content = pyproject["tool"]["poetry"]

    content["name"] = "poetry"
    content["version"] = __version__
    content["description"] = ""
    content["authors"] = ["Sébastien Eustace <sebastien@eustace.io>"]

    dependency_section = content["dependencies"]
    dependency_section["python"] = "^3.6"

    env.path.joinpath("pyproject.toml").write_text(
        tomlkit.dumps(pyproject), encoding="utf-8"
    )


@pytest.fixture(autouse=True)
def install_plugin(
    env: "MockEnv", installed: "Repository", pyproject: None, mocker: "MockerFixture"
):
    env.path.joinpath("plugins.toml").write_text(
        'poetry-plugin = "^1.2.3"\n', encoding="utf-8"
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


def test_remove_installed_package(
    app: "PoetryTestApplication", tester: "CommandTester", env: "MockEnv"
):
    tester.execute("poetry-plugin")

    expected = """\
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 0 installs, 0 updates, 1 removal

  • Removing poetry-plugin (1.2.3)
"""

    assert tester.io.fetch_output() == expected

    content = tomlkit.loads(
        env.path.joinpath("plugins.toml").read_text(encoding="utf-8")
    )
    assert "poetry-plugin" not in content


def test_remove_installed_package_dry_run(
    app: "PoetryTestApplication", tester: "CommandTester", env: "MockEnv"
):
    tester.execute("poetry-plugin --dry-run")

    expected = """\
Updating dependencies
Resolving dependencies...

Package operations: 0 installs, 0 updates, 1 removal, 1 skipped

  • Removing poetry-plugin (1.2.3)
  • Removing poetry-plugin (1.2.3)
  • Installing poetry (1.2.0a2): Skipped for the following reason: Already installed
"""

    assert tester.io.fetch_output() == expected

    content = tomlkit.loads(
        env.path.joinpath("plugins.toml").read_text(encoding="utf-8")
    )
    assert "poetry-plugin" in content
