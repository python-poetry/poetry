from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar
from typing import Protocol

import pytest

from cleo.io.buffered_io import BufferedIO
from poetry.core.constraints.version import Version
from poetry.core.packages.project_package import ProjectPackage

from poetry.packages.locker import Locker
from poetry.plugins import ApplicationPlugin
from poetry.plugins import Plugin
from poetry.plugins.plugin_manager import PluginManager
from poetry.poetry import Poetry
from tests.helpers import mock_metadata_entry_points


if TYPE_CHECKING:
    from cleo.io.io import IO
    from pytest_mock import MockerFixture

    from poetry.console.commands.command import Command
    from tests.conftest import Config
    from tests.types import FixtureDirGetter


class ManagerFactory(Protocol):
    def __call__(self, group: str = Plugin.group) -> PluginManager: ...


class MyPlugin(Plugin):
    def activate(self, poetry: Poetry, io: IO) -> None:
        io.write_line("Setting readmes")
        poetry.package.readmes = (Path("README.md"),)


class MyCommandPlugin(ApplicationPlugin):
    commands: ClassVar[list[type[Command]]] = []


class InvalidPlugin:
    def activate(self, poetry: Poetry, io: IO) -> None:
        io.write_line("Updating version")
        poetry.package.version = Version.parse("9.9.9")


@pytest.fixture
def poetry(fixture_dir: FixtureDirGetter, config: Config) -> Poetry:
    project_path = fixture_dir("simple_project")
    poetry = Poetry(
        project_path / "pyproject.toml",
        {},
        ProjectPackage("simple-project", "1.2.3"),
        Locker(project_path / "poetry.lock", {}),
        config,
    )

    return poetry


@pytest.fixture()
def io() -> IO:
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
    with_my_plugin: None,
) -> None:
    manager = manager_factory()
    manager.load_plugins()
    manager.activate(poetry, io)

    assert poetry.package.readmes == (Path("README.md"),)
    assert io.fetch_output() == "Setting readmes\n"


@pytest.fixture
def with_my_plugin(mocker: MockerFixture) -> None:
    mock_metadata_entry_points(mocker, MyPlugin)


@pytest.fixture
def with_invalid_plugin(mocker: MockerFixture) -> None:
    mock_metadata_entry_points(mocker, InvalidPlugin)


def test_load_plugins_with_invalid_plugin(
    manager_factory: ManagerFactory,
    poetry: Poetry,
    io: BufferedIO,
    with_invalid_plugin: None,
) -> None:
    manager = manager_factory()

    with pytest.raises(ValueError):
        manager.load_plugins()


def test_load_plugins_with_plugins_disabled(
    no_plugin_manager: PluginManager,
    poetry: Poetry,
    io: BufferedIO,
    with_my_plugin: None,
) -> None:
    no_plugin_manager.load_plugins()

    assert poetry.package.version.text == "1.2.3"
    assert io.fetch_output() == ""
