from typing import TYPE_CHECKING
from typing import Type

import pytest

from entrypoints import EntryPoint as _EntryPoint
from poetry.core.packages.package import Package

from poetry.factory import Factory
from poetry.plugins.application_plugin import ApplicationPlugin
from poetry.plugins.plugin import Plugin


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.plugins.base_plugin import BasePlugin
    from poetry.repositories import Repository
    from tests.helpers import PoetryTestApplication
    from tests.types import CommandTesterFactory


class EntryPoint(_EntryPoint):
    def load(self) -> Type["BasePlugin"]:
        if "ApplicationPlugin" in self.object_name:
            return ApplicationPlugin

        return Plugin


@pytest.fixture()
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
    return command_tester_factory("plugin show")


def test_show_displays_installed_plugins(
    app: "PoetryTestApplication",
    tester: "CommandTester",
    installed: "Repository",
    mocker: "MockerFixture",
):
    mocker.patch(
        "entrypoints.get_group_all",
        side_effect=[
            [
                EntryPoint(
                    "poetry-plugin",
                    "poetry_plugin.plugins:ApplicationPlugin",
                    "FirstApplicationPlugin",
                )
            ],
            [
                EntryPoint(
                    "poetry-plugin",
                    "poetry_plugin.plugins:Plugin",
                    "FirstPlugin",
                )
            ],
        ],
    )

    installed.add_package(Package("poetry-plugin", "1.2.3"))

    tester.execute("")

    expected = """
  • poetry-plugin (1.2.3)
      1 plugin and 1 application plugin
"""

    assert tester.io.fetch_output() == expected


def test_show_displays_installed_plugins_with_multiple_plugins(
    app: "PoetryTestApplication",
    tester: "CommandTester",
    installed: "Repository",
    mocker: "MockerFixture",
):
    mocker.patch(
        "entrypoints.get_group_all",
        side_effect=[
            [
                EntryPoint(
                    "poetry-plugin",
                    "poetry_plugin.plugins:ApplicationPlugin",
                    "FirstApplicationPlugin",
                ),
                EntryPoint(
                    "poetry-plugin",
                    "poetry_plugin.plugins:ApplicationPlugin",
                    "SecondApplicationPlugin",
                ),
            ],
            [
                EntryPoint(
                    "poetry-plugin",
                    "poetry_plugin.plugins:Plugin",
                    "FirstPlugin",
                ),
                EntryPoint(
                    "poetry-plugin",
                    "poetry_plugin.plugins:Plugin",
                    "SecondPlugin",
                ),
            ],
        ],
    )

    installed.add_package(Package("poetry-plugin", "1.2.3"))

    tester.execute("")

    expected = """
  • poetry-plugin (1.2.3)
      2 plugins and 2 application plugins
"""

    assert tester.io.fetch_output() == expected


def test_show_displays_installed_plugins_with_dependencies(
    app: "PoetryTestApplication",
    tester: "CommandTester",
    installed: "Repository",
    mocker: "MockerFixture",
):
    mocker.patch(
        "entrypoints.get_group_all",
        side_effect=[
            [
                EntryPoint(
                    "poetry-plugin",
                    "poetry_plugin.plugins:ApplicationPlugin",
                    "FirstApplicationPlugin",
                )
            ],
            [
                EntryPoint(
                    "poetry-plugin",
                    "poetry_plugin.plugins:Plugin",
                    "FirstPlugin",
                )
            ],
        ],
    )

    plugin = Package("poetry-plugin", "1.2.3")
    plugin.add_dependency(Factory.create_dependency("foo", ">=1.2.3"))
    plugin.add_dependency(Factory.create_dependency("bar", "<4.5.6"))
    installed.add_package(plugin)

    tester.execute("")

    expected = """
  • poetry-plugin (1.2.3)
      1 plugin and 1 application plugin

      Dependencies
        - foo (>=1.2.3)
        - bar (<4.5.6)
"""

    assert tester.io.fetch_output() == expected
