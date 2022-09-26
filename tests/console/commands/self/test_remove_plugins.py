from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import tomlkit

from poetry.core.packages.dependency import Dependency
from poetry.core.packages.package import Package
from poetry.core.packages.project_package import ProjectPackage

from poetry.__version__ import __version__
from poetry.console.commands.self.self_command import SelfCommand
from poetry.factory import Factory
from tests.console.commands.self.utils import get_self_command_dependencies


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.repositories import Repository
    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("self remove")


@pytest.fixture(autouse=True)
def install_plugin(installed: Repository) -> None:
    package = ProjectPackage("poetry-instance", __version__)
    plugin = Package("poetry-plugin", "1.2.3")

    package.add_dependency(
        Dependency(plugin.name, "^1.2.3", groups=[SelfCommand.ADDITIONAL_PACKAGE_GROUP])
    )
    content = Factory.create_pyproject_from_package(package)
    system_pyproject_file = SelfCommand.get_default_system_pyproject_file()
    system_pyproject_file.write_text(content.as_string(), encoding="utf-8")

    lock_content = {
        "package": [
            {
                "name": "poetry-plugin",
                "version": "1.2.3",
                "category": "main",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
        ],
        "metadata": {
            "python-versions": "^3.6",
            "platform": "*",
            "content-hash": "123456789",
            "files": {"poetry-plugin": []},
        },
    }
    system_pyproject_file.parent.joinpath("poetry.lock").write_text(
        tomlkit.dumps(lock_content), encoding="utf-8"
    )

    installed.add_package(plugin)


def test_remove_installed_package(tester: CommandTester):
    tester.execute("poetry-plugin")

    expected = """\
Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 0 installs, 0 updates, 1 removal

  • Removing poetry-plugin (1.2.3)
"""
    assert tester.io.fetch_output() == expected

    dependencies = get_self_command_dependencies()

    assert "poetry-plugin" not in dependencies
    assert not dependencies


def test_remove_installed_package_dry_run(tester: CommandTester):
    tester.execute("poetry-plugin --dry-run")

    expected = f"""\
Updating dependencies
Resolving dependencies...

Package operations: 0 installs, 0 updates, 1 removal, 1 skipped

  • Removing poetry-plugin (1.2.3)
  • Installing poetry ({__version__}): Skipped for the following reason: Already \
installed
"""

    assert tester.io.fetch_output() == expected

    dependencies = get_self_command_dependencies()

    assert "poetry-plugin" in dependencies
