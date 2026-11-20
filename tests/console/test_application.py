from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys

from typing import TYPE_CHECKING
from typing import ClassVar
from typing import cast

import pytest

from cleo.testers.application_tester import ApplicationTester

from poetry.console.application import Application
from poetry.console.commands.command import Command
from poetry.plugins.application_plugin import ApplicationPlugin
from poetry.plugins.plugin_manager import ProjectPluginCache
from poetry.repositories.cached_repository import CachedRepository
from poetry.utils.authenticator import Authenticator
from poetry.utils.env import EnvManager
from poetry.utils.env import MockEnv
from tests.helpers import mock_metadata_entry_points


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.io.inputs.argv_input import ArgvInput
    from pytest_mock import MockerFixture

    from tests.helpers import PoetryTestApplication
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


@pytest.mark.parametrize("command", ["install", "sync"])
@pytest.mark.parametrize("no_plugins", [False, True])
@pytest.mark.parametrize("already_installed", [False, True])
def test_install_activates_new_project_plugins(
    command: str,
    no_plugins: bool,
    already_installed: bool,
    mocker: MockerFixture,
    set_project_context: SetProjectContext,
) -> None:
    from cleo.events.console_events import TERMINATE

    from poetry.plugins.plugin_manager import PluginManager

    installed = already_installed
    activated = []
    terminated = []

    class ProjectPlugin(AddCommandPlugin):
        def activate(self, application: Application) -> None:
            super().activate(application)
            activated.append(application)
            assert application.event_dispatcher is not None
            application.event_dispatcher.add_listener(
                TERMINATE, lambda *args: terminated.append(command)
            )

    # Keep the same entry point identity when querying metadata a second time.
    ep = mocker.Mock()
    ep.name = "project-plugin"
    ep.group = ApplicationPlugin.group
    ep.dist = None
    ep.load.return_value = ProjectPlugin
    mocker.patch(
        "poetry.plugins.plugin_manager.metadata.entry_points",
        side_effect=lambda **kwargs: (
            [ep] if installed and kwargs.get("group") == ApplicationPlugin.group else []
        ),
    )

    def ensure_plugins(*args: object) -> None:
        nonlocal installed
        installed = True

    ensure = mocker.patch.object(
        PluginManager, "ensure_project_plugins", side_effect=ensure_plugins
    )
    mocker.patch("poetry.installation.installer.Installer.run", return_value=0)

    with set_project_context("sample_project"):
        app = Application()
        tester = ApplicationTester(app)
        tester.execute(f"{command} --no-root" + (" --no-plugins" if no_plugins else ""))

    assert tester.status_code == 0
    assert len(activated) == (0 if no_plugins else 1)
    assert terminated == ([] if no_plugins else [command])
    assert ensure.call_count == (0 if no_plugins else 1)
    if not no_plugins:
        assert app.find("foo").name == "foo"


@pytest.mark.parametrize("command", ["install", "sync"])
def test_install_processes_only_new_project_plugin_pth_files(
    command: str,
    tmp_path: Path,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    set_project_context: SetProjectContext,
) -> None:
    from poetry.plugins.plugin_manager import PluginManager

    marker = tmp_path / "executions.txt"
    monkeypatch.setattr(sys, "path", sys.path.copy())
    env = mocker.Mock()
    env.sys_path = sys.path
    mocker.patch.object(EnvManager, "get_system_env", return_value=env)
    mocker.patch("poetry.installation.installer.Installer.run", return_value=0)

    with set_project_context("sample_project") as project:
        plugin_path = project / ProjectPluginCache.PATH
        plugin_path.mkdir(parents=True)
        (plugin_path / "old.pth").write_text(
            f"import pathlib; pathlib.Path({str(marker)!r}).open('a').write('old\\n')\n"
        )

        def ensure_plugins(*args: object) -> None:
            (plugin_path / "new.pth").write_text(
                f"import pathlib; pathlib.Path({str(marker)!r}).open('a').write('new\\n')\n"
            )

        mocker.patch.object(
            PluginManager, "ensure_project_plugins", side_effect=ensure_plugins
        )
        tester = ApplicationTester(Application())
        tester.execute(f"{command} --no-root")

    assert tester.status_code == 0
    assert marker.read_text() == "old\nnew\n"


def test_application_execute_plugin_command_with_plugins_disabled(
    with_add_command_plugin: None,
) -> None:
    app = Application()

    tester = ApplicationTester(app)
    tester.execute("foo --no-plugins")

    assert tester.io.fetch_output() == ""
    assert "The requested command foo does not exist." in tester.io.fetch_error()
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
            (_name, _args, kwargs) = call
            assert "disable_cache" in kwargs
            assert disable_cache is kwargs["disable_cache"]


@pytest.mark.parametrize(
    ("tokens", "result"),
    [
        (
            ["-C", "/path/working/dir", "env", "list"],
            ["--directory", "/path/working/dir", "env", "list"],
        ),
        (
            ["-P", "/path/project/dir", "env", "list"],
            ["--project", "/path/project/dir", "env", "list"],
        ),
        (
            ["-P/path/project/dir", "env", "list"],
            ["--project", "/path/project/dir", "env", "list"],
        ),
        (
            ["-v", "run", "-P/path/project/dir", "echo", "--help"],
            [
                "--verbose",
                "--project",
                "/path/project/dir",
                "run",
                "--",
                "echo",
                "--help",
            ],
        ),
        (
            ["--no-ansi", "run", "-V", "python", "-V"],
            ["--version", "--no-ansi", "run", "--", "python", "-V"],
        ),
        (
            ["--no-ansi", "run", "-V", "--", "python", "-V"],
            ["--version", "--no-ansi", "run", "--", "python", "-V"],
        ),
    ],
)
def test_application_input_configuration_and_sorting(
    tokens: list[str], result: list[str], app: PoetryTestApplication
) -> None:
    app.create_io()
    assert app._io is not None

    io_input = cast("ArgvInput", app._io.input)
    io_input._tokens = tokens

    app._configure_io(app._io)
    app._sort_global_options(app._io)

    io_input = cast("ArgvInput", app._io.input)
    assert io_input._tokens == result


def test_no_slow_imports_when_importing_the_cli_entrypoint() -> None:
    """
    This test checks that modules that are slow to import
    (and not required for all commands) are not imported
    when importing the CLI entrypoint.
    """
    code = (
        "import sys, json;"
        "import poetry.console.application;"
        "print(json.dumps(sorted(sys.modules)))"
    )
    loaded_modules = json.loads(
        subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        ).stdout
    )
    assert "requests" not in loaded_modules
    assert "urllib3" not in loaded_modules
