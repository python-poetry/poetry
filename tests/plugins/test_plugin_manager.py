from pathlib import Path

import pytest

from cleo.io.buffered_io import BufferedIO
from entrypoints import EntryPoint

from poetry.packages.locker import Locker
from poetry.packages.project_package import ProjectPackage
from poetry.plugins import ApplicationPlugin
from poetry.plugins import Plugin
from poetry.plugins.plugin_manager import PluginManager
from poetry.poetry import Poetry


CWD = Path(__file__).parent.parent / "fixtures" / "simple_project"


class MyPlugin(Plugin):
    def activate(self, poetry, io):
        io.write_line("Updating version")
        poetry.package.set_version("9.9.9")


class MyCommandPlugin(ApplicationPlugin):
    @property
    def commands(self):
        return []


class InvalidPlugin:
    def activate(self, poetry, io):
        io.write_line("Updating version")
        poetry.package.version = "9.9.9"


@pytest.fixture()
def poetry(tmp_dir, config):
    poetry = Poetry(
        CWD / "pyproject.toml",
        {},
        ProjectPackage("simple-project", "1.2.3"),
        Locker(CWD / "poetry.lock", {}),
        config,
    )

    return poetry


@pytest.fixture()
def io():
    return BufferedIO()


@pytest.fixture()
def manager_factory(poetry, io):
    def _manager(type="plugin"):
        return PluginManager(type)

    return _manager


@pytest.fixture()
def no_plugin_manager(poetry, io):
    return PluginManager("plugin", disable_plugins=True)


def test_load_plugins_and_activate(manager_factory, poetry, io, mocker):
    manager = manager_factory()

    mocker.patch(
        "entrypoints.get_group_all",
        return_value=[
            EntryPoint("my-plugin", "tests.plugins.test_plugin_manager", "MyPlugin")
        ],
    )

    manager.load_plugins()
    manager.activate(poetry, io)

    assert "9.9.9" == poetry.package.version.text
    assert "Updating version\n" == io.fetch_output()


def test_load_plugins_with_invalid_plugin(manager_factory, poetry, io, mocker):
    manager = manager_factory()

    mocker.patch(
        "entrypoints.get_group_all",
        return_value=[
            EntryPoint(
                "my-plugin", "tests.plugins.test_plugin_manager", "InvalidPlugin"
            )
        ],
    )

    with pytest.raises(ValueError):
        manager.load_plugins()


def test_load_plugins_with_plugins_disabled(no_plugin_manager, poetry, io, mocker):
    mocker.patch(
        "entrypoints.get_group_all",
        return_value=[
            EntryPoint("my-plugin", "tests.plugins.test_plugin_manager", "MyPlugin")
        ],
    )

    no_plugin_manager.load_plugins()

    assert "1.2.3" == poetry.package.version.text
    assert "" == io.fetch_output()
