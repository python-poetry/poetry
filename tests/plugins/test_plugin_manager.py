from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cleo.io.buffered_io import BufferedIO
from entrypoints import EntryPoint
from poetry.core.packages.project_package import ProjectPackage

from poetry.packages.locker import Locker
from poetry.plugins import ApplicationPlugin
from poetry.plugins import Plugin
from poetry.plugins.plugin_manager import PluginManager
from poetry.poetry import Poetry
from tests.compat import Protocol


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tests.conftest import Config

CWD = Path(__file__).parent.parent / "fixtures" / "simple_project"


class ManagerFactory(Protocol):
    def __call__(self, group: str = Plugin.group) -> PluginManager:
        ...


class MyPlugin(Plugin):
    def activate(self, poetry: Poetry, io: BufferedIO) -> None:
        io.write_line("Setting readme")
        poetry.package.readme = "README.md"


class MyCommandPlugin(ApplicationPlugin):
    commands = []


class InvalidPlugin:
    def activate(self, poetry: Poetry, io: BufferedIO) -> None:
        io.write_line("Updating version")
        poetry.package.version = "9.9.9"


@pytest.fixture()
def poetry(tmp_dir: str, config: Config) -> Poetry:
    poetry = Poetry(
        CWD / "pyproject.toml",
        {},
        ProjectPackage("simple-project", "1.2.3"),
        Locker(CWD / "poetry.lock", {}),
        config,
    )

    return poetry


@pytest.fixture()
def io() -> BufferedIO:
    return BufferedIO()


@pytest.fixture()
def manager_factory(poetry: Poetry, io: BufferedIO) -> ManagerFactory:
    def _manager(group: str = Plugin.group) -> PluginManager:
        return PluginManager(group)

    return _manager


@pytest.fixture()
def no_plugin_manager(poetry: Poetry, io: BufferedIO) -> PluginManager:
    return PluginManager(Plugin.group, disable_plugins=True)


def test_load_plugins_and_activate(
    manager_factory: ManagerFactory,
    poetry: Poetry,
    io: BufferedIO,
    mocker: MockerFixture,
):
    manager = manager_factory()

    mocker.patch(
        "entrypoints.get_group_all",
        return_value=[
            EntryPoint("my-plugin", "tests.plugins.test_plugin_manager", "MyPlugin")
        ],
    )

    manager.load_plugins()
    manager.activate(poetry, io)

    assert poetry.package.readme == "README.md"
    assert io.fetch_output() == "Setting readme\n"


def test_load_plugins_with_invalid_plugin(
    manager_factory: ManagerFactory,
    poetry: Poetry,
    io: BufferedIO,
    mocker: MockerFixture,
):
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


def test_load_plugins_with_plugins_disabled(
    no_plugin_manager: PluginManager,
    poetry: Poetry,
    io: BufferedIO,
    mocker: MockerFixture,
):
    mocker.patch(
        "entrypoints.get_group_all",
        return_value=[
            EntryPoint("my-plugin", "tests.plugins.test_plugin_manager", "MyPlugin")
        ],
    )

    no_plugin_manager.load_plugins()

    assert poetry.package.version.text == "1.2.3"
    assert io.fetch_output() == ""
