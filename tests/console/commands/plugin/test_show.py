import pytest

from entrypoints import EntryPoint as _EntryPoint

from poetry.__version__ import __version__
from poetry.core.packages.package import Package
from poetry.factory import Factory
from poetry.plugins.application_plugin import ApplicationPlugin
from poetry.plugins.plugin import Plugin
from poetry.repositories.installed_repository import InstalledRepository
from poetry.repositories.pool import Pool
from poetry.utils.env import EnvManager


class EntryPoint(_EntryPoint):
    def load(self):
        if "ApplicationPlugin" in self.object_name:
            return ApplicationPlugin

        return Plugin


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("plugin show")


@pytest.fixture()
def installed():
    repository = InstalledRepository()

    repository.add_package(Package("poetry", __version__))

    return repository


def configure_sources_factory(repo):
    def _configure_sources(poetry, sources, config, io):
        pool = Pool()
        pool.add_repository(repo)
        poetry.set_pool(pool)

    return _configure_sources


@pytest.fixture(autouse=True)
def setup_mocks(mocker, env, repo, installed):
    mocker.patch.object(EnvManager, "get_system_env", return_value=env)
    mocker.patch.object(InstalledRepository, "load", return_value=installed)
    mocker.patch.object(
        Factory, "configure_sources", side_effect=configure_sources_factory(repo)
    )


def test_show_displays_installed_plugins(app, tester, installed, mocker):
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
    app, tester, installed, mocker
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
    app, tester, installed, mocker
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
