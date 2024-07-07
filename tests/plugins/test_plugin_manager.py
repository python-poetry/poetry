from __future__ import annotations

import shutil

from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar
from typing import Protocol

import pytest

from cleo.io.buffered_io import BufferedIO
from cleo.io.outputs.output import Verbosity
from poetry.core.constraints.version import Version
from poetry.core.packages.dependency import Dependency
from poetry.core.packages.file_dependency import FileDependency
from poetry.core.packages.package import Package
from poetry.core.packages.project_package import ProjectPackage

from poetry.factory import Factory
from poetry.installation.wheel_installer import WheelInstaller
from poetry.packages.locker import Locker
from poetry.plugins import ApplicationPlugin
from poetry.plugins import Plugin
from poetry.plugins.plugin_manager import PluginManager
from poetry.plugins.plugin_manager import ProjectPluginCache
from poetry.poetry import Poetry
from poetry.puzzle.exceptions import SolverProblemError
from poetry.repositories import Repository
from poetry.repositories import RepositoryPool
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils.env import Env
from poetry.utils.env import EnvManager
from poetry.utils.env import MockEnv
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
def repo() -> Repository:
    repo = Repository("repo")
    repo.add_package(Package("my-other-plugin", "1.0"))
    for version in ("1.0", "2.0"):
        package = Package("my-application-plugin", version)
        package.add_dependency(Dependency("some-lib", version))
        repo.add_package(package)
        repo.add_package(Package("some-lib", version))
    return repo


@pytest.fixture
def pool(repo: Repository) -> RepositoryPool:
    pool = RepositoryPool()
    pool.add_repository(repo)

    return pool


@pytest.fixture
def system_env(tmp_path: Path, mocker: MockerFixture) -> Env:
    env = MockEnv(path=tmp_path, sys_path=[str(tmp_path / "purelib")])
    mocker.patch.object(EnvManager, "get_system_env", return_value=env)
    return env


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


@pytest.fixture
def poetry_with_plugins(
    fixture_dir: FixtureDirGetter, pool: RepositoryPool, tmp_path: Path
) -> Poetry:
    orig_path = fixture_dir("project_plugins")
    project_path = tmp_path / "project"
    project_path.mkdir()
    shutil.copy(orig_path / "pyproject.toml", project_path / "pyproject.toml")
    poetry = Factory().create_poetry(project_path)
    poetry.set_pool(pool)
    return poetry


@pytest.fixture()
def io() -> BufferedIO:
    return BufferedIO()


@pytest.fixture()
def manager_factory(poetry: Poetry, io: BufferedIO) -> ManagerFactory:
    def _manager(group: str = Plugin.group) -> PluginManager:
        return PluginManager(group)

    return _manager


@pytest.fixture
def with_my_plugin(mocker: MockerFixture) -> None:
    mock_metadata_entry_points(mocker, MyPlugin)


@pytest.fixture
def with_invalid_plugin(mocker: MockerFixture) -> None:
    mock_metadata_entry_points(mocker, InvalidPlugin)


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


def test_load_plugins_with_invalid_plugin(
    manager_factory: ManagerFactory,
    poetry: Poetry,
    io: BufferedIO,
    with_invalid_plugin: None,
) -> None:
    manager = manager_factory()

    with pytest.raises(ValueError):
        manager.load_plugins()


def test_add_project_plugin_path(
    poetry_with_plugins: Poetry,
    io: BufferedIO,
    system_env: Env,
    fixture_dir: FixtureDirGetter,
) -> None:
    dist_info_1 = "my_application_plugin-1.0.dist-info"
    dist_info_2 = "my_application_plugin-2.0.dist-info"
    cache = ProjectPluginCache(poetry_with_plugins, io)
    shutil.copytree(
        fixture_dir("project_plugins") / dist_info_1, cache._path / dist_info_1
    )
    shutil.copytree(
        fixture_dir("project_plugins") / dist_info_2, system_env.purelib / dist_info_2
    )

    assert {
        f"{p.name} {p.version}" for p in InstalledRepository.load(system_env).packages
    } == {"my-application-plugin 2.0"}

    PluginManager.add_project_plugin_path(poetry_with_plugins.pyproject_path.parent)

    assert {
        f"{p.name} {p.version}" for p in InstalledRepository.load(system_env).packages
    } == {"my-application-plugin 1.0"}


def test_ensure_plugins_no_plugins_no_output(poetry: Poetry, io: BufferedIO) -> None:
    PluginManager.ensure_project_plugins(poetry, io)

    assert not (poetry.pyproject_path.parent / ProjectPluginCache.PATH).exists()
    assert io.fetch_output() == ""
    assert io.fetch_error() == ""


def test_ensure_plugins_no_plugins_existing_cache_is_removed(
    poetry: Poetry, io: BufferedIO
) -> None:
    plugin_path = poetry.pyproject_path.parent / ProjectPluginCache.PATH
    plugin_path.mkdir(parents=True)

    PluginManager.ensure_project_plugins(poetry, io)

    assert not plugin_path.exists()
    assert io.fetch_output() == (
        "No project plugins defined. Removing the project's plugin cache\n\n"
    )
    assert io.fetch_error() == ""


@pytest.mark.parametrize("debug_out", [False, True])
def test_ensure_plugins_no_output_if_fresh(
    poetry_with_plugins: Poetry, io: BufferedIO, debug_out: bool
) -> None:
    io.set_verbosity(Verbosity.DEBUG if debug_out else Verbosity.NORMAL)
    cache = ProjectPluginCache(poetry_with_plugins, io)
    cache._write_config()

    cache.ensure_plugins()

    assert cache._config_file.exists()
    assert (
        cache._gitignore_file.exists()
        and cache._gitignore_file.read_text(encoding="utf-8") == "*"
    )
    assert io.fetch_output() == (
        "The project's plugin cache is up to date.\n\n" if debug_out else ""
    )
    assert io.fetch_error() == ""


@pytest.mark.parametrize("debug_out", [False, True])
def test_ensure_plugins_ignore_irrelevant_markers(
    poetry_with_plugins: Poetry, io: BufferedIO, debug_out: bool
) -> None:
    io.set_verbosity(Verbosity.DEBUG if debug_out else Verbosity.NORMAL)
    poetry_with_plugins.local_config["requires-plugins"] = {
        "irrelevant": {"version": "1.0", "markers": "python_version < '3'"}
    }
    cache = ProjectPluginCache(poetry_with_plugins, io)

    cache.ensure_plugins()

    assert cache._config_file.exists()
    assert (
        cache._gitignore_file.exists()
        and cache._gitignore_file.read_text(encoding="utf-8") == "*"
    )
    assert io.fetch_output() == (
        "No relevant project plugins for Poetry's environment defined.\n\n"
        if debug_out
        else ""
    )
    assert io.fetch_error() == ""


def test_ensure_plugins_remove_outdated(
    poetry_with_plugins: Poetry, io: BufferedIO, fixture_dir: FixtureDirGetter
) -> None:
    # Test with irrelevant plugins because this is the first return
    # where it is relevant that an existing cache is removed.
    poetry_with_plugins.local_config["requires-plugins"] = {
        "irrelevant": {"version": "1.0", "markers": "python_version < '3'"}
    }
    fixture_path = fixture_dir("project_plugins")
    cache = ProjectPluginCache(poetry_with_plugins, io)
    cache._path.mkdir(parents=True)
    dist_info = "my_application_plugin-1.0.dist-info"
    shutil.copytree(fixture_path / dist_info, cache._path / dist_info)
    cache._config_file.touch()

    cache.ensure_plugins()

    assert cache._config_file.exists()
    assert not (cache._path / dist_info).exists()
    assert io.fetch_output() == (
        "Removing the project's plugin cache because it is outdated\n"
    )
    assert io.fetch_error() == ""


def test_ensure_plugins_ignore_already_installed_in_system_env(
    poetry_with_plugins: Poetry,
    io: BufferedIO,
    system_env: Env,
    fixture_dir: FixtureDirGetter,
) -> None:
    fixture_path = fixture_dir("project_plugins")
    for dist_info in (
        "my_application_plugin-2.0.dist-info",
        "my_other_plugin-1.0.dist-info",
    ):
        shutil.copytree(fixture_path / dist_info, system_env.purelib / dist_info)
    cache = ProjectPluginCache(poetry_with_plugins, io)

    cache.ensure_plugins()

    assert cache._config_file.exists()
    assert (
        cache._gitignore_file.exists()
        and cache._gitignore_file.read_text(encoding="utf-8") == "*"
    )
    assert io.fetch_output() == (
        "Ensuring that the Poetry plugins required by the project are available...\n"
        "All required plugins have already been installed in Poetry's environment.\n\n"
    )
    assert io.fetch_error() == ""


def test_ensure_plugins_install_missing_plugins(
    poetry_with_plugins: Poetry,
    io: BufferedIO,
    system_env: Env,
    fixture_dir: FixtureDirGetter,
    mocker: MockerFixture,
) -> None:
    cache = ProjectPluginCache(poetry_with_plugins, io)
    install_spy = mocker.spy(cache, "_install")
    execute_mock = mocker.patch(
        "poetry.plugins.plugin_manager.Installer._execute", return_value=0
    )

    cache.ensure_plugins()

    install_spy.assert_called_once_with(
        [
            Dependency("my-application-plugin", ">=2.0"),
            Dependency("my-other-plugin", ">=1.0"),
        ],
        system_env,
        [],
    )
    execute_mock.assert_called_once()
    assert [repr(op) for op in execute_mock.call_args.args[0] if not op.skipped] == [
        "<Install some-lib (2.0)>",
        "<Install my-application-plugin (2.0)>",
        "<Install my-other-plugin (1.0)>",
    ]
    assert cache._config_file.exists()
    assert (
        cache._gitignore_file.exists()
        and cache._gitignore_file.read_text(encoding="utf-8") == "*"
    )
    assert io.fetch_output() == (
        "Ensuring that the Poetry plugins required by the project are available...\n"
        "The following Poetry plugins are required by the project"
        " but are not installed in Poetry's environment:\n"
        "  - my-application-plugin (>=2.0)\n"
        "  - my-other-plugin (>=1.0)\n"
        "Installing Poetry plugins only for the current project...\n"
        "Updating dependencies\n"
        "Resolving dependencies...\n\n"
        "Writing lock file\n\n"
    )
    assert io.fetch_error() == ""


def test_ensure_plugins_install_only_missing_plugins(
    poetry_with_plugins: Poetry,
    io: BufferedIO,
    system_env: Env,
    fixture_dir: FixtureDirGetter,
    mocker: MockerFixture,
) -> None:
    fixture_path = fixture_dir("project_plugins")
    for dist_info in (
        "my_application_plugin-2.0.dist-info",
        "some_lib-2.0.dist-info",
    ):
        shutil.copytree(fixture_path / dist_info, system_env.purelib / dist_info)
    cache = ProjectPluginCache(poetry_with_plugins, io)
    install_spy = mocker.spy(cache, "_install")
    execute_mock = mocker.patch(
        "poetry.plugins.plugin_manager.Installer._execute", return_value=0
    )

    cache.ensure_plugins()

    install_spy.assert_called_once_with(
        [Dependency("my-other-plugin", ">=1.0")],
        system_env,
        [Package("my-application-plugin", "2.0"), Package("some-lib", "2.0")],
    )
    execute_mock.assert_called_once()
    assert [repr(op) for op in execute_mock.call_args.args[0] if not op.skipped] == [
        "<Install my-other-plugin (1.0)>"
    ]
    assert cache._config_file.exists()
    assert (
        cache._gitignore_file.exists()
        and cache._gitignore_file.read_text(encoding="utf-8") == "*"
    )
    assert io.fetch_output() == (
        "Ensuring that the Poetry plugins required by the project are available...\n"
        "The following Poetry plugins are required by the project"
        " but are not installed in Poetry's environment:\n"
        "  - my-other-plugin (>=1.0)\n"
        "Installing Poetry plugins only for the current project...\n"
        "Updating dependencies\n"
        "Resolving dependencies...\n\n"
        "Writing lock file\n\n"
    )
    assert io.fetch_error() == ""


@pytest.mark.parametrize("debug_out", [False, True])
def test_ensure_plugins_install_overwrite_wrong_version_plugins(
    poetry_with_plugins: Poetry,
    io: BufferedIO,
    system_env: Env,
    fixture_dir: FixtureDirGetter,
    mocker: MockerFixture,
    debug_out: bool,
) -> None:
    io.set_verbosity(Verbosity.DEBUG if debug_out else Verbosity.NORMAL)
    fixture_path = fixture_dir("project_plugins")
    for dist_info in (
        "my_application_plugin-1.0.dist-info",
        "some_lib-2.0.dist-info",
    ):
        shutil.copytree(fixture_path / dist_info, system_env.purelib / dist_info)
    cache = ProjectPluginCache(poetry_with_plugins, io)
    install_spy = mocker.spy(cache, "_install")
    execute_mock = mocker.patch(
        "poetry.plugins.plugin_manager.Installer._execute", return_value=0
    )

    cache.ensure_plugins()

    install_spy.assert_called_once_with(
        [
            Dependency("my-application-plugin", ">=2.0"),
            Dependency("my-other-plugin", ">=1.0"),
        ],
        system_env,
        [Package("some-lib", "2.0")],
    )
    execute_mock.assert_called_once()
    assert [repr(op) for op in execute_mock.call_args.args[0] if not op.skipped] == [
        "<Install my-application-plugin (2.0)>",
        "<Install my-other-plugin (1.0)>",
    ]
    assert cache._config_file.exists()
    assert (
        cache._gitignore_file.exists()
        and cache._gitignore_file.read_text(encoding="utf-8") == "*"
    )
    start = (
        "Ensuring that the Poetry plugins required by the project are available...\n"
    )
    opt = (
        "The following Poetry plugins are required by the project"
        " but are not satisfied by the installed versions:\n"
        "  - my-application-plugin (>=2.0)\n"
        "    installed: my-application-plugin (1.0)\n"
    )
    end = (
        "The following Poetry plugins are required by the project"
        " but are not installed in Poetry's environment:\n"
        "  - my-application-plugin (>=2.0)\n"
        "  - my-other-plugin (>=1.0)\n"
        "Installing Poetry plugins only for the current project...\n"
    )
    expected = (start + opt + end) if debug_out else (start + end)
    assert io.fetch_output().startswith(expected)
    assert io.fetch_error() == ""


def test_ensure_plugins_pins_other_installed_packages(
    poetry_with_plugins: Poetry,
    io: BufferedIO,
    system_env: Env,
    fixture_dir: FixtureDirGetter,
    mocker: MockerFixture,
) -> None:
    fixture_path = fixture_dir("project_plugins")
    for dist_info in (
        "my_application_plugin-1.0.dist-info",
        "some_lib-1.0.dist-info",
    ):
        shutil.copytree(fixture_path / dist_info, system_env.purelib / dist_info)
    cache = ProjectPluginCache(poetry_with_plugins, io)
    install_spy = mocker.spy(cache, "_install")
    execute_mock = mocker.patch(
        "poetry.plugins.plugin_manager.Installer._execute", return_value=0
    )

    with pytest.raises(SolverProblemError):
        cache.ensure_plugins()

    install_spy.assert_called_once_with(
        [
            Dependency("my-application-plugin", ">=2.0"),
            Dependency("my-other-plugin", ">=1.0"),
        ],
        system_env,
        # pinned because it might be a dependency of another plugin or Poetry itself
        [Package("some-lib", "1.0")],
    )
    execute_mock.assert_not_called()
    assert not cache._config_file.exists()
    assert (
        cache._gitignore_file.exists()
        and cache._gitignore_file.read_text(encoding="utf-8") == "*"
    )
    assert io.fetch_output() == (
        "Ensuring that the Poetry plugins required by the project are available...\n"
        "The following Poetry plugins are required by the project"
        " but are not installed in Poetry's environment:\n"
        "  - my-application-plugin (>=2.0)\n"
        "  - my-other-plugin (>=1.0)\n"
        "Installing Poetry plugins only for the current project...\n"
        "Updating dependencies\n"
        "Resolving dependencies...\n"
    )
    assert io.fetch_error() == ""


@pytest.mark.parametrize("other_version", [False, True])
def test_project_plugins_are_installed_in_project_folder(
    poetry_with_plugins: Poetry,
    io: BufferedIO,
    system_env: Env,
    fixture_dir: FixtureDirGetter,
    tmp_path: Path,
    other_version: bool,
) -> None:
    orig_purelib = system_env.purelib
    orig_platlib = system_env.platlib

    # make sure that the path dependency is on the same drive (for Windows tests in CI)
    orig_wheel_path = (
        fixture_dir("wheel_with_no_requires_dist") / "demo-0.1.0-py2.py3-none-any.whl"
    )
    wheel_path = tmp_path / orig_wheel_path.name
    shutil.copy(orig_wheel_path, wheel_path)

    if other_version:
        WheelInstaller(system_env).install(wheel_path)
        dist_info = orig_purelib / "demo-0.1.0.dist-info"
        metadata = dist_info / "METADATA"
        metadata.write_text(
            metadata.read_text(encoding="utf-8").replace("0.1.0", "0.1.2"),
            encoding="utf-8",
        )
        dist_info.rename(orig_purelib / "demo-0.1.2.dist-info")

    cache = ProjectPluginCache(poetry_with_plugins, io)

    # just use a file dependency so that we do not have to set up a repository
    cache._install([FileDependency("demo", wheel_path)], system_env, [])

    project_site_packages = [p.name for p in cache._path.iterdir()]
    assert "demo" in project_site_packages
    assert "demo-0.1.0.dist-info" in project_site_packages

    orig_site_packages = [p.name for p in orig_purelib.iterdir()]
    if other_version:
        assert "demo" in orig_site_packages
        assert "demo-0.1.2.dist-info" in orig_site_packages
        assert "demo-0.1.0.dist-info" not in orig_site_packages
    else:
        assert not any(p.startswith("demo") for p in orig_site_packages)
    if orig_platlib != orig_purelib:
        assert not any(p.name.startswith("demo") for p in orig_platlib.iterdir())
