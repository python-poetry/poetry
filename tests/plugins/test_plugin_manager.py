from pathlib import Path
<<<<<<< HEAD
from typing import TYPE_CHECKING
from typing import List
=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

import pytest

from cleo.io.buffered_io import BufferedIO
from entrypoints import EntryPoint

from poetry.packages.locker import Locker
from poetry.packages.project_package import ProjectPackage
from poetry.plugins import ApplicationPlugin
from poetry.plugins import Plugin
from poetry.plugins.plugin_manager import PluginManager
from poetry.poetry import Poetry
<<<<<<< HEAD
from tests.compat import Protocol


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tests.conftest import Config

CWD = Path(__file__).parent.parent / "fixtures" / "simple_project"


class ManagerFactory(Protocol):
    def __call__(self, type: str = "plugin") -> PluginManager:
        ...


class MyPlugin(Plugin):
    def activate(self, poetry: Poetry, io: BufferedIO) -> None:
=======


CWD = Path(__file__).parent.parent / "fixtures" / "simple_project"


class MyPlugin(Plugin):
    def activate(self, poetry, io):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        io.write_line("Updating version")
        poetry.package.set_version("9.9.9")


class MyCommandPlugin(ApplicationPlugin):
    @property
<<<<<<< HEAD
    def commands(self) -> List[str]:
=======
    def commands(self):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        return []


class InvalidPlugin:
<<<<<<< HEAD
    def activate(self, poetry: Poetry, io: BufferedIO) -> None:
=======
    def activate(self, poetry, io):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        io.write_line("Updating version")
        poetry.package.version = "9.9.9"


@pytest.fixture()
<<<<<<< HEAD
def poetry(tmp_dir: str, config: "Config") -> Poetry:
=======
def poetry(tmp_dir, config):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    poetry = Poetry(
        CWD / "pyproject.toml",
        {},
        ProjectPackage("simple-project", "1.2.3"),
        Locker(CWD / "poetry.lock", {}),
        config,
    )

    return poetry


@pytest.fixture()
<<<<<<< HEAD
def io() -> BufferedIO:
=======
def io():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return BufferedIO()


@pytest.fixture()
<<<<<<< HEAD
def manager_factory(poetry: Poetry, io: BufferedIO) -> ManagerFactory:
    def _manager(type: str = "plugin") -> PluginManager:
=======
def manager_factory(poetry, io):
    def _manager(type="plugin"):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        return PluginManager(type)

    return _manager


@pytest.fixture()
<<<<<<< HEAD
def no_plugin_manager(poetry: Poetry, io: BufferedIO) -> PluginManager:
    return PluginManager("plugin", disable_plugins=True)


def test_load_plugins_and_activate(
    manager_factory: ManagerFactory,
    poetry: Poetry,
    io: BufferedIO,
    mocker: "MockerFixture",
):
=======
def no_plugin_manager(poetry, io):
    return PluginManager("plugin", disable_plugins=True)


def test_load_plugins_and_activate(manager_factory, poetry, io, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    manager = manager_factory()

    mocker.patch(
        "entrypoints.get_group_all",
        return_value=[
            EntryPoint("my-plugin", "tests.plugins.test_plugin_manager", "MyPlugin")
        ],
    )

    manager.load_plugins()
    manager.activate(poetry, io)

<<<<<<< HEAD
    assert poetry.package.version.text == "9.9.9"
    assert io.fetch_output() == "Updating version\n"


def test_load_plugins_with_invalid_plugin(
    manager_factory: ManagerFactory,
    poetry: Poetry,
    io: BufferedIO,
    mocker: "MockerFixture",
):
=======
    assert "9.9.9" == poetry.package.version.text
    assert "Updating version\n" == io.fetch_output()


def test_load_plugins_with_invalid_plugin(manager_factory, poetry, io, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_load_plugins_with_plugins_disabled(
    no_plugin_manager: PluginManager,
    poetry: Poetry,
    io: BufferedIO,
    mocker: "MockerFixture",
):
=======
def test_load_plugins_with_plugins_disabled(no_plugin_manager, poetry, io, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.patch(
        "entrypoints.get_group_all",
        return_value=[
            EntryPoint("my-plugin", "tests.plugins.test_plugin_manager", "MyPlugin")
        ],
    )

    no_plugin_manager.load_plugins()

<<<<<<< HEAD
    assert poetry.package.version.text == "1.2.3"
    assert io.fetch_output() == ""
=======
    assert "1.2.3" == poetry.package.version.text
    assert "" == io.fetch_output()
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
