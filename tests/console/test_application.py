from __future__ import annotations

import re
import shutil

from typing import TYPE_CHECKING
from typing import ClassVar

import pytest

from cleo.testers.application_tester import ApplicationTester

from poetry.console.application import Application
from poetry.console.commands.command import Command
from poetry.plugins.application_plugin import ApplicationPlugin
from poetry.plugins.plugin_manager import ProjectPluginCache
from poetry.repositories.cached_repository import CachedRepository
from poetry.utils.authenticator import Authenticator
from poetry.utils.env import EnvManager
from tests.helpers import mock_metadata_entry_points
from tests.utils.env.helpers import MockEnv


if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from tests.types import FixtureDirGetter
    from tests.types import SetProjectContext


class FooCommand(Command):
    name = "foo"

    description = "Foo Command"

    def handle(self) -> int:
        self.line("foo called")

        return 0


class AddCommandPlugin(ApplicationPlugin):
    commands: ClassVar[list[type[Command]]] = [FooCommand]


@pytest.fixture
def with_add_command_plugin(mocker: MockerFixture) -> None:
    mock_metadata_entry_points(mocker, AddCommandPlugin)


def test_application_with_plugins(with_add_command_plugin: None) -> None:
    app = Application()

    tester = ApplicationTester(app)
    tester.execute("")

    assert re.search(r"\s+foo\s+Foo Command", tester.io.fetch_output()) is not None
    assert tester.status_code == 0


def test_application_with_plugins_disabled(with_add_command_plugin: None) -> None:
    app = Application()

    tester = ApplicationTester(app)
    tester.execute("--no-plugins")

    assert re.search(r"\s+foo\s+Foo Command", tester.io.fetch_output()) is None
    assert tester.status_code == 0


def test_application_execute_plugin_command(with_add_command_plugin: None) -> None:
    app = Application()

    tester = ApplicationTester(app)
    tester.execute("foo")

    assert tester.io.fetch_output() == "foo called\n"
    assert tester.status_code == 0


def test_application_execute_plugin_command_with_plugins_disabled(
    with_add_command_plugin: None,
) -> None:
    app = Application()

    tester = ApplicationTester(app)
    tester.execute("foo --no-plugins")

    assert tester.io.fetch_output() == ""
    assert tester.io.fetch_error() == '\nThe command "foo" does not exist.\n'
    assert tester.status_code == 1


@pytest.mark.parametrize("with_project_plugins", [False, True])
@pytest.mark.parametrize("no_plugins", [False, True])
def test_application_project_plugins(
    fixture_dir: FixtureDirGetter,
    tmp_path: Path,
    no_plugins: bool,
    with_project_plugins: bool,
    mocker: MockerFixture,
    set_project_context: SetProjectContext,
) -> None:
    env = MockEnv(
        path=tmp_path / "env", version_info=(3, 8, 0), sys_path=[str(tmp_path / "env")]
    )
    mocker.patch.object(EnvManager, "get_system_env", return_value=env)

    orig_dir = fixture_dir("project_plugins")
    project_path = tmp_path / "project"
    project_path.mkdir()
    shutil.copy(orig_dir / "pyproject.toml", project_path / "pyproject.toml")
    project_plugin_path = project_path / ProjectPluginCache.PATH
    if with_project_plugins:
        project_plugin_path.mkdir(parents=True)

    with set_project_context(project_path, in_place=True):
        app = Application()

        tester = ApplicationTester(app)
        tester.execute("--no-plugins" if no_plugins else "")

    assert tester.status_code == 0
    sys_path = EnvManager.get_system_env(naive=True).sys_path
    if with_project_plugins and not no_plugins:
        assert sys_path[0] == str(project_plugin_path)
    else:
        assert sys_path[0] != str(project_plugin_path)


@pytest.mark.parametrize("disable_cache", [True, False])
def test_application_verify_source_cache_flag(
    disable_cache: bool, set_project_context: SetProjectContext
) -> None:
    with set_project_context("sample_project"):
        app = Application()

        tester = ApplicationTester(app)
        command = "debug info"

        if disable_cache:
            command = f"{command} --no-cache"

        assert not app._poetry

        tester.execute(command)

        assert app.poetry.pool.repositories

        for repo in app.poetry.pool.repositories:
            assert isinstance(repo, CachedRepository)
            assert repo._disable_cache == disable_cache


@pytest.mark.parametrize("disable_cache", [True, False])
def test_application_verify_cache_flag_at_install(
    mocker: MockerFixture,
    disable_cache: bool,
    set_project_context: SetProjectContext,
) -> None:
    import poetry.utils.authenticator

    # Set default authenticator to None so that it is recreated for each test
    # and we get a consistent call_count.
    poetry.utils.authenticator._authenticator = None

    with set_project_context("sample_project"):
        app = Application()

        tester = ApplicationTester(app)
        command = "install --dry-run"

        if disable_cache:
            command = f"{command} --no-cache"

        spy = mocker.spy(Authenticator, "__init__")

        tester.execute(command)

        # The third call is the default authenticator, which ignores the cache flag.
        assert spy.call_count == 3
        for call in spy.mock_calls[:2]:
            (name, args, kwargs) = call
            assert "disable_cache" in kwargs
            assert disable_cache is kwargs["disable_cache"]
