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

    content = Factory.create_legacy_pyproject_from_package(package)
    content["dependency-groups"] = tomlkit.table()
    content["dependency-groups"][SelfCommand.ADDITIONAL_PACKAGE_GROUP] = tomlkit.array(  # type: ignore[index]
        "[\n]"
    )
    content["dependency-groups"][SelfCommand.ADDITIONAL_PACKAGE_GROUP].append(  # type: ignore[index, union-attr, call-arg]
        Dependency(plugin.name, "^1.2.3").to_pep_508()
    )

    system_pyproject_file = SelfCommand.get_default_system_pyproject_file()
    with open(system_pyproject_file, "w", encoding="utf-8", newline="") as f:
        f.write(content.as_string())

    lock_content = {
        "package": [
            {
                "name": "poetry-plugin",
                "version": "1.2.3",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "files": [],
            },
        ],
        "metadata": {
            "lock-version": "2.0",
            "python-versions": "^3.6",
            "content-hash": "123456789",
        },
    }
    system_pyproject_file.parent.joinpath("poetry.lock").write_text(
        tomlkit.dumps(lock_content), encoding="utf-8"
    )

    installed.add_package(plugin)


def test_remove_installed_package(tester: CommandTester) -> None:
    tester.execute("poetry-plugin")

    expected = """\
Updating dependencies
Resolving dependencies...

Package operations: 0 installs, 0 updates, 1 removal

  - Removing poetry-plugin (1.2.3)

Writing lock file
"""
    assert tester.io.fetch_output() == expected

    dependencies = get_self_command_dependencies()

    assert not dependencies


def test_remove_installed_package_dry_run(tester: CommandTester) -> None:
    tester.execute("poetry-plugin --dry-run")

    expected = f"""\
Updating dependencies
Resolving dependencies...

Package operations: 0 installs, 0 updates, 1 removal, 1 skipped

  - Removing poetry-plugin (1.2.3)
  - Installing poetry ({__version__}): Skipped for the following reason: Already \
installed
"""

    assert tester.io.fetch_output() == expected

    dependencies = get_self_command_dependencies()

    assert dependencies
    assert len(dependencies) == 1
    assert "poetry-plugin" in dependencies[0]
