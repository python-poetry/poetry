from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.core.packages.dependency import Dependency
from poetry.core.packages.package import Package
from poetry.core.packages.project_package import ProjectPackage

from poetry.__version__ import __version__
from poetry.console.commands.self.self_command import SelfCommand
from poetry.factory import Factory
from tests.console.commands.self.utils import get_self_command_dependencies


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("plugin remove")


def test_deprecation_warning(tester: CommandTester, repo: TestRepository) -> None:
    plugin = Package("poetry-plugin", "1.2.3")

    repo.add_package(Package("poetry", __version__))
    repo.add_package(plugin)

    package = ProjectPackage("poetry-instance", __version__)
    package.add_dependency(
        Dependency(plugin.name, "^1.2.3", groups=[SelfCommand.ADDITIONAL_PACKAGE_GROUP])
    )

    content = Factory.create_pyproject_from_package(package)
    system_pyproject_file = SelfCommand.get_default_system_pyproject_file()
    system_pyproject_file.write_text(content.as_string(), encoding="utf-8")

    dependencies = get_self_command_dependencies(locked=False)
    assert "poetry-plugin" in dependencies

    tester.execute("poetry-plugin")

    assert (
        tester.io.fetch_error()
        == "This command is deprecated. Use self remove command instead.\n"
    )

    dependencies = get_self_command_dependencies()
    assert "poetry-plugin" not in dependencies
    assert not dependencies
