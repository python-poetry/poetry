from __future__ import annotations

import contextlib
import logging
import os
import platform
import re
import shutil
import sys

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import PropertyMock

import findpython
import httpretty
import keyring
import packaging.version
import pytest

from installer.utils import SCHEME_NAMES
from jaraco.classes import properties
from keyring.backend import KeyringBackend
from keyring.backends.fail import Keyring as FailKeyring
from keyring.credentials import SimpleCredential
from keyring.errors import KeyringError
from keyring.errors import KeyringLocked
from packaging.utils import canonicalize_name
from poetry.core.constraints.version import parse_constraint
from poetry.core.packages.dependency import Dependency
from poetry.core.version.markers import parse_marker
from pytest import FixtureRequest

from poetry.config.config import Config as BaseConfig
from poetry.config.dict_config_source import DictConfigSource
from poetry.console.commands.command import Command
from poetry.factory import Factory
from poetry.layouts import layout
from poetry.packages.direct_origin import _get_package_from_git
from poetry.repositories import Repository
from poetry.repositories import RepositoryPool
from poetry.repositories.exceptions import PackageNotFoundError
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils.cache import ArtifactCache
from poetry.utils.env import EnvManager
from poetry.utils.env import MockEnv
from poetry.utils.env import SystemEnv
from poetry.utils.env import VirtualEnv
from poetry.utils.env.python import Python
from poetry.utils.password_manager import PoetryKeyring
from tests.helpers import MOCK_DEFAULT_GIT_REVISION
from tests.helpers import TestLocker
from tests.helpers import TestRepository
from tests.helpers import get_package
from tests.helpers import http_setup_redirect
from tests.helpers import isolated_environment
from tests.helpers import mock_clone
from tests.helpers import set_keyring_backend
from tests.helpers import switch_working_directory
from tests.helpers import with_working_directory


if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Mapping
    from typing import Any
    from typing import Callable
    from unittest.mock import MagicMock

    from cleo.io.inputs.argument import Argument
    from cleo.io.inputs.option import Option
    from keyring.credentials import Credential
    from packaging.utils import NormalizedName
    from poetry.core.packages.package import Package
    from pytest import Config as PyTestConfig
    from pytest import Parser
    from pytest import TempPathFactory
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.types import CommandFactory
    from tests.types import FixtureCopier
    from tests.types import FixtureDirGetter
    from tests.types import MockedPythonRegister
    from tests.types import PackageFactory
    from tests.types import ProjectFactory
    from tests.types import SetProjectContext


pytest_plugins = [
    "tests.repositories.fixtures",
]


def pytest_addoption(parser: Parser) -> None:
    parser.addoption(
        "--integration",
        action="store_true",
        dest="integration",
        default=False,
        help="enable integration tests",
    )


def pytest_configure(config: PyTestConfig) -> None:
    config.addinivalue_line("markers", "integration: mark integration tests")

    if not config.option.integration:
        if config.option.markexpr:
            config.option.markexpr += " and not integration"
        else:
            config.option.markexpr = "not integration"


class Config(BaseConfig):
    _config_source: DictConfigSource
    _auth_config_source: DictConfigSource

    def get(self, setting_name: str, default: Any = None) -> Any:
        self.merge(self._config_source.config)
        self.merge(self._auth_config_source.config)

        return super().get(setting_name, default=default)

    def raw(self) -> dict[str, Any]:
        self.merge(self._config_source.config)
        self.merge(self._auth_config_source.config)

        return super().raw()

    def all(self) -> dict[str, Any]:
        self.merge(self._config_source.config)
        self.merge(self._auth_config_source.config)

        return super().all()


class DummyBackend(KeyringBackend):
    def __init__(self) -> None:
        self._passwords: dict[str, dict[str, str]] = {}
        self._service_defaults: dict[str, Credential] = {}

    @properties.classproperty
    def priority(self) -> float:
        return 42

    def set_password(self, service: str, username: str, password: str) -> None:
        self._passwords[service] = {username: password}

    def get_password(self, service: str, username: str) -> str | None:
        return self._passwords.get(service, {}).get(username)

    def get_credential(
        self,
        service: str,
        username: str | None,
    ) -> Credential | None:
        if username is None:
            credential = self._service_defaults.get(service)
            return credential

        password = self.get_password(service, username)
        if password is None:
            return None

        return SimpleCredential(username, password)

    def delete_password(self, service: str, username: str) -> None:
        if service in self._passwords and username in self._passwords[service]:
            del self._passwords[service][username]

    def set_default_service_credential(
        self, service: str, credential: Credential
    ) -> None:
        self._service_defaults[service] = credential


class LockedBackend(KeyringBackend):
    @properties.classproperty
    def priority(self) -> float:
        return 42

    def set_password(self, service: str, username: str, password: str) -> None:
        raise KeyringLocked()

    def get_password(self, service: str, username: str) -> str | None:
        raise KeyringLocked()

    def get_credential(
        self,
        service: str,
        username: str | None,
    ) -> Credential | None:
        raise KeyringLocked()

    def delete_password(self, service: str, username: str) -> None:
        raise KeyringLocked()


class ErroneousBackend(FailKeyring):
    @properties.classproperty
    def priority(self) -> float:
        return 42

    def get_credential(
        self,
        service: str,
        username: str | None,
    ) -> Credential | None:
        raise KeyringError()


@pytest.fixture()
def poetry_keyring() -> PoetryKeyring:
    return PoetryKeyring("poetry-repository")


@pytest.fixture()
def dummy_keyring() -> DummyBackend:
    return DummyBackend()


@pytest.fixture()
def with_simple_keyring(dummy_keyring: DummyBackend) -> None:
    set_keyring_backend(dummy_keyring)


@pytest.fixture()
def with_fail_keyring() -> None:
    set_keyring_backend(FailKeyring())  # type: ignore[no-untyped-call]


@pytest.fixture()
def with_locked_keyring() -> None:
    set_keyring_backend(LockedBackend())  # type: ignore[no-untyped-call]


@pytest.fixture()
def with_erroneous_keyring() -> None:
    set_keyring_backend(ErroneousBackend())  # type: ignore[no-untyped-call]


@pytest.fixture()
def with_null_keyring() -> None:
    from keyring.backends.null import Keyring

    set_keyring_backend(Keyring())  # type: ignore[no-untyped-call]


@pytest.fixture()
def with_chained_fail_keyring(mocker: MockerFixture) -> None:
    mocker.patch(
        "keyring.backend.get_all_keyring",
        lambda: [FailKeyring()],  # type: ignore[no-untyped-call]
    )
    from keyring.backends.chainer import ChainerBackend

    set_keyring_backend(ChainerBackend())  # type: ignore[no-untyped-call]


@pytest.fixture()
def with_chained_null_keyring(mocker: MockerFixture) -> None:
    from keyring.backends.null import Keyring

    mocker.patch(
        "keyring.backend.get_all_keyring",
        lambda: [Keyring()],  # type: ignore[no-untyped-call]
    )
    from keyring.backends.chainer import ChainerBackend

    set_keyring_backend(ChainerBackend())  # type: ignore[no-untyped-call]


@pytest.fixture
def config_cache_dir(tmp_path: Path) -> Path:
    path = tmp_path / ".cache" / "pypoetry"
    path.mkdir(parents=True)
    return path


@pytest.fixture
def config_data_dir(tmp_path: Path) -> Path:
    path = tmp_path / ".local" / "share" / "pypoetry"
    path.mkdir(parents=True)
    return path


@pytest.fixture
def config_virtualenvs_path(config_cache_dir: Path) -> Path:
    return config_cache_dir / "virtualenvs"


@pytest.fixture
def config_source(config_cache_dir: Path, config_data_dir: Path) -> DictConfigSource:
    source = DictConfigSource()
    source.add_property("cache-dir", str(config_cache_dir))
    source.add_property("data-dir", str(config_data_dir))

    return source


@pytest.fixture
def auth_config_source() -> DictConfigSource:
    source = DictConfigSource()

    return source


@pytest.fixture(autouse=True)
def config(
    config_source: DictConfigSource,
    auth_config_source: DictConfigSource,
    mocker: MockerFixture,
) -> Config:
    keyring.set_keyring(FailKeyring())  # type: ignore[no-untyped-call]

    c = Config()
    c.merge(config_source.config)
    c.set_config_source(config_source)
    c.set_auth_config_source(auth_config_source)

    mocker.patch("poetry.config.config.Config.create", return_value=c)
    mocker.patch("poetry.config.config.Config.set_config_source")

    return c


@pytest.fixture
def artifact_cache(config: Config) -> ArtifactCache:
    return ArtifactCache(cache_dir=config.artifacts_cache_directory)


@pytest.fixture()
def config_dir(tmp_path: Path) -> Path:
    path = tmp_path / "config"
    path.mkdir()
    return path


@pytest.fixture(autouse=True)
def mock_user_config_dir(mocker: MockerFixture, config_dir: Path) -> None:
    mocker.patch("poetry.locations.CONFIG_DIR", new=config_dir)
    mocker.patch("poetry.config.config.CONFIG_DIR", new=config_dir)


@pytest.fixture
def environ() -> Iterator[None]:
    with isolated_environment():
        yield


@pytest.fixture(autouse=True)
def isolate_environ() -> Iterator[None]:
    """Ensure the environment is isolated from user configuration."""
    with isolated_environment():
        for var in os.environ:
            if var.startswith("POETRY_") or var in {"PYTHONPATH", "VIRTUAL_ENV"}:
                del os.environ[var]

        yield


@pytest.fixture(autouse=True)
def git_mock(mocker: MockerFixture, request: FixtureRequest) -> None:
    if request.node.get_closest_marker("skip_git_mock"):
        return

    # Patch git module to not actually clone projects
    mocker.patch("poetry.vcs.git.Git.clone", new=mock_clone)
    p = mocker.patch("poetry.vcs.git.Git.get_revision")
    p.return_value = MOCK_DEFAULT_GIT_REVISION

    _get_package_from_git.cache_clear()


@pytest.fixture
def http() -> Iterator[type[httpretty.httpretty]]:
    httpretty.reset()
    with httpretty.enabled(allow_net_connect=False, verbose=True):
        yield httpretty


@pytest.fixture
def http_redirector(http: type[httpretty.httpretty]) -> None:
    http_setup_redirect(http, http.HEAD, http.GET, http.PUT, http.POST)


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def fixture_base() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixture_dir(fixture_base: Path) -> FixtureDirGetter:
    def _fixture_dir(name: str) -> Path:
        return fixture_base / name

    return _fixture_dir


@pytest.fixture
def tmp_venv(tmp_path: Path) -> Iterator[VirtualEnv]:
    venv_path = tmp_path / "venv"

    EnvManager.build_venv(venv_path)

    venv = VirtualEnv(venv_path)
    yield venv

    shutil.rmtree(venv.path)


@pytest.fixture
def installed() -> InstalledRepository:
    return InstalledRepository()


@pytest.fixture(scope="session")
def current_env() -> SystemEnv:
    return SystemEnv(Path(sys.executable))


@pytest.fixture(scope="session")
def current_python(current_env: SystemEnv) -> tuple[int, int, int]:
    return current_env.version_info[:3]


@pytest.fixture(scope="session")
def default_python(current_python: tuple[int, int, int]) -> str:
    return "^" + ".".join(str(v) for v in current_python[:2])


@pytest.fixture
def repo(http: type[httpretty.httpretty]) -> TestRepository:
    http.register_uri(
        http.GET,
        re.compile("^https?://foo.bar/(.+?)$"),
    )
    return TestRepository(name="foo")


@pytest.fixture
def project_factory(
    tmp_path: Path,
    config: Config,
    repo: TestRepository,
    installed: InstalledRepository,
    default_python: str,
    load_required_fixtures: None,
) -> ProjectFactory:
    workspace = tmp_path

    def _factory(
        name: str | None = None,
        dependencies: Mapping[str, str] | None = None,
        dev_dependencies: Mapping[str, str] | None = None,
        pyproject_content: str | None = None,
        poetry_lock_content: str | None = None,
        install_deps: bool = True,
        source: Path | None = None,
        locker_config: dict[str, Any] | None = None,
        use_test_locker: bool = True,
    ) -> Poetry:
        project_dir = workspace / f"poetry-fixture-{name}"
        dependencies = dependencies or {}
        dev_dependencies = dev_dependencies or {}

        if pyproject_content or source:
            if source:
                project_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source, project_dir)
            else:
                project_dir.mkdir(parents=True, exist_ok=True)

            if pyproject_content:
                with (project_dir / "pyproject.toml").open("w", encoding="utf-8") as f:
                    f.write(pyproject_content)
        else:
            assert name is not None
            layout("src")(
                name,
                "0.1.0",
                author="PyTest Tester <mc.testy@testface.com>",
                readme_format="md",
                python=default_python,
                dependencies=dependencies,
                dev_dependencies=dev_dependencies,
            ).create(project_dir, with_tests=False)

        if poetry_lock_content:
            lock_file = project_dir / "poetry.lock"
            lock_file.write_text(data=poetry_lock_content, encoding="utf-8")

        poetry = Factory().create_poetry(project_dir)

        if use_test_locker:
            locker = TestLocker(
                poetry.locker.lock, locker_config or poetry.locker._pyproject_data
            )
            locker.write()

            poetry.set_locker(locker)

        poetry.set_config(config)

        pool = RepositoryPool()
        pool.add_repository(repo)

        poetry.set_pool(pool)

        if install_deps:
            for deps in [dependencies, dev_dependencies]:
                for name, version in deps.items():
                    pkg = get_package(name, version)
                    repo.add_package(pkg)
                    installed.add_package(pkg)

        return poetry

    return _factory


@pytest.fixture
def create_package(repo: Repository) -> PackageFactory:
    """
    This function is a pytest fixture that creates a factory function to generate
    and customize package objects. These packages are added to the default repository
    fixture and configured with specific versions, optional extras, and self-referenced
    extras. This helps in setting up package dependencies for testing purposes.

    :return: A factory function that can be used to create and configure packages.
    """

    def create_new_package(
        name: str,
        version: str | None = None,
        dependencies: list[Dependency] | None = None,
        extras: dict[str, list[str]] | None = None,
    ) -> Package:
        version = version or "1.0"
        package = get_package(name, version)

        package_extras: dict[NormalizedName, list[Dependency]] = {}

        for extra, extra_dependencies in (extras or {}).items():
            extra = canonicalize_name(extra)

            if extra not in package_extras:
                package_extras[extra] = []

            for extra_dependency_spec in extra_dependencies:
                extra_dependency = Dependency.create_from_pep_508(extra_dependency_spec)
                extra_dependency._optional = True
                extra_dependency.marker = extra_dependency.marker.intersect(
                    parse_marker(f"extra == '{extra}'")
                )

                if extra_dependency.name != package.name:
                    assert extra_dependency.constraint.allows(package.version)

                    # if it is not a self-referencing dependency, make sure we add it to the repo
                    try:
                        pkg = repo.package(extra_dependency.name, package.version)
                    except PackageNotFoundError:
                        pkg = get_package(extra_dependency.name, str(package.version))
                        repo.add_package(pkg)

                    extra_dependency.constraint = parse_constraint(f"^{pkg.version}")

                    # if requirement already exists in the package, update the marker
                    for requirement in package.requires:
                        if (
                            requirement.name == extra_dependency.name
                            and requirement.is_optional()
                        ):
                            requirement.marker = requirement.marker.union(
                                extra_dependency.marker
                            )
                            break
                    else:
                        package.add_dependency(extra_dependency)

                package_extras[extra].append(extra_dependency)

        package.extras = package_extras

        for dependency in dependencies or []:
            package.add_dependency(dependency)

        repo.add_package(package)

        return package

    return create_new_package


@pytest.fixture(autouse=True)
def set_simple_log_formatter() -> None:
    """
    This fixture removes any formatting added via IOFormatter.
    """
    for name in logging.Logger.manager.loggerDict:
        for handler in logging.getLogger(name).handlers:
            # replace formatter with simple formatter for testing
            handler.setFormatter(logging.Formatter(fmt="%(message)s"))


@pytest.fixture
def fixture_copier(fixture_base: Path, tmp_path: Path) -> FixtureCopier:
    def _copy(relative_path: str, target: Path | None = None) -> Path:
        path = fixture_base / relative_path
        target = target or (tmp_path / relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            return target

        if path.is_dir():
            shutil.copytree(path, target)
        else:
            shutil.copyfile(path, target)

        return target

    return _copy


@pytest.fixture
def required_fixtures() -> list[str]:
    return []


@pytest.fixture(autouse=True)
def load_required_fixtures(
    required_fixtures: list[str], fixture_copier: FixtureCopier
) -> None:
    for fixture in required_fixtures:
        fixture_copier(fixture)


@pytest.fixture
def venv_flags_default() -> dict[str, bool]:
    return {
        "always-copy": False,
        "system-site-packages": False,
        "no-pip": False,
    }


@pytest.fixture(autouse=(os.name == "nt"))
def httpretty_windows_mock_urllib3_wait_for_socket(mocker: MockerFixture) -> None:
    # this is a workaround for https://github.com/gabrielfalcao/HTTPretty/issues/442
    mocker.patch("urllib3.util.wait.select_wait_for_socket", returns=True)


@pytest.fixture
def disable_http_status_force_list(mocker: MockerFixture) -> Iterator[None]:
    mocker.patch("poetry.utils.authenticator.STATUS_FORCELIST", [])
    yield


@pytest.fixture(autouse=True)
def tmp_working_directory(tmp_path: Path) -> Iterator[Path]:
    with switch_working_directory(tmp_path):
        yield tmp_path


@pytest.fixture(autouse=True, scope="session")
def tmp_session_working_directory(tmp_path_factory: TempPathFactory) -> Iterator[Path]:
    tmp_path = tmp_path_factory.mktemp("session-working-directory")
    with switch_working_directory(tmp_path):
        yield tmp_path


@pytest.fixture
def set_project_context(
    tmp_working_directory: Path, tmp_path: Path, fixture_dir: FixtureDirGetter
) -> SetProjectContext:
    @contextlib.contextmanager
    def project_context(project: str | Path, in_place: bool = False) -> Iterator[Path]:
        if isinstance(project, str):
            project = fixture_dir(project)

        with with_working_directory(
            source=project,
            target=tmp_path.joinpath(project.name) if not in_place else None,
        ) as path:
            yield path

    return project_context


@pytest.fixture
def command_factory() -> CommandFactory:
    """
    Provides a pytest fixture for creating mock commands using a factory function.

    This fixture allows for customization of command attributes like name,
    arguments, options, description, help text, and handler.
    """

    def _command_factory(
        command_name: str,
        command_arguments: list[Argument] | None = None,
        command_options: list[Option] | None = None,
        command_description: str = "",
        command_help: str = "",
        command_handler: Callable[[Command], int] | str | None = None,
    ) -> Command:
        class MockCommand(Command):
            name = command_name
            arguments = command_arguments or []
            options = command_options or []
            description = command_description
            help = command_help

            def handle(self) -> int:
                if command_handler is not None and not isinstance(command_handler, str):
                    return command_handler(self)

                self._io.write_line(
                    command_handler
                    or f"The mock command '{command_name}' has been called"
                )

                return 0

        return MockCommand()

    return _command_factory


@pytest.fixture(autouse=True)
def default_keyring(with_null_keyring: None) -> None:
    pass


@pytest.fixture
def system_env(tmp_path_factory: TempPathFactory, mocker: MockerFixture) -> SystemEnv:
    base_path = tmp_path_factory.mktemp("system_env")
    env = MockEnv(path=base_path, sys_path=[str(base_path / "purelib")])
    assert env.path.is_dir()

    userbase = env.path / "userbase"
    userbase.mkdir(exist_ok=False)
    env.paths["userbase"] = str(userbase)

    paths = {str(scheme): str(env.path / scheme) for scheme in SCHEME_NAMES}
    env.paths.update(paths)

    for path in paths.values():
        Path(path).mkdir(exist_ok=False)

    mocker.patch.object(EnvManager, "get_system_env", return_value=env)

    env.set_paths()
    return env


@pytest.fixture
def mocked_pythons() -> list[findpython.PythonVersion]:
    """
    Fixture that provides a mock representation of Python versions that are registered.

    This fixture returns a list of `findpython.PythonVersion` objects. Typically,
    it is used in test scenarios to replace actual Python version discovery with
    mocked data. By default, this fixture returns an empty list to simulate an
    environment without any Python installations.

    :return: Mocked list of Python versions with the type of
        `findpython.PythonVersion`.
    """
    return []


@pytest.fixture
def mocked_pythons_version_map() -> dict[str, findpython.PythonVersion]:
    """
    Create a mocked Python version map for testing purposes. This serves as a
    quick lookup for exact version matches.

    This function provides a fixture that returns a dictionary containing a
    mapping of specific keys to corresponding instances of the
    `findpython.PythonVersion` class. This is primarily used for testing
    scenarios involving multiple Python interpreters. If the key is an
    empty string, it maps to the system Python interpreter as used by the
    `with_mocked_findpython` fixture.

    :return: A dictionary mapping string keys to `findpython.PythonVersion`
        instances. A default key "" (empty string) is pre-set to match the
        current system environment.
    """
    return {
        # add the system python if key is empty
        "": Python.get_system_python()._python
    }


@pytest.fixture
def mock_findpython_find(
    mocked_pythons: list[findpython.PythonVersion],
    mocked_pythons_version_map: dict[str, findpython.PythonVersion],
    mocker: MockerFixture,
) -> MagicMock:
    """
    Mock the `findpython.find` function for testing purposes, enabling controlled
    execution and predictable results when specific python versions or executables
    are queried. This mock is particularly useful for reproducing various scenarios
    involving Python version detection without dependence on the actual system's
    Python installations.

    :return:
        A `MagicMock` object representing the mocked `findpython.find` function. It
        operates using the `_find` internal function, which resolves python versions
        based on the provided test data (`mocked_pythons` and
        `mocked_pythons_version_map`).

    """

    def _find(
        name: str | None = None,
    ) -> findpython.PythonVersion | None:
        # find exact version matches
        # the default key is an empty string in mocked_pythons_version_map
        if python := mocked_pythons_version_map.get(name or ""):
            return python

        if name is None:
            return None

        candidates: list[findpython.PythonVersion] = []

        # iterate through to find executable name match
        for python in mocked_pythons:
            if python.executable.name == name:
                return python
            elif str(python.executable).endswith(name):
                candidates.append(python)

        if candidates:
            candidates.sort(key=lambda p: p.executable.name)
            return candidates[0]

        return None

    return mocker.patch(
        "findpython.find",
        side_effect=_find,
    )


@pytest.fixture
def mock_findpython_find_all(
    mocked_pythons: list[findpython.PythonVersion],
    mocker: MockerFixture,
) -> MagicMock:
    """
    Mocks the `find_all` function in the `findpython` module to return a predefined
    list of `PythonVersion` objects.

    This fixture is useful for testing functionality dependent on the output of the
    `find_all` function without executing its original logic.

    :return: Mocked `find_all` function patched to return the specified list of
        `mocked_pythons`.
    """
    return mocker.patch(
        "findpython.find_all",
        return_value=mocked_pythons,
    )


@pytest.fixture
def mocked_python_register(
    with_mocked_findpython: None,
    mocked_pythons: list[findpython.PythonVersion],
    mocked_pythons_version_map: dict[str, findpython.PythonVersion],
    mocker: MockerFixture,
) -> MockedPythonRegister:
    """
    Fixture to provide a mocked registration mechanism for PythonVersion objects. The
    fixture interacts with mocked versions of Python, allowing test cases to register
    and manage Python versions under controlled conditions. The provided register
    function enables the dynamic registration of Python versions, executable,
    and optional system designation.

    :return: A function to register a Python version with configurable options.
    """

    def register(
        version: str,
        executable_name: str | Path | None = None,
        parent: str | Path | None = None,
        make_system: bool = False,
    ) -> Python:
        # we allow this to let windows specific tests setup special cases
        parent = Path(parent or "/usr/bin")

        if not executable_name:
            info = version.split(".")
            executable_name = f"python{info[0]}.{info[1]}"

        python = findpython.PythonVersion(
            executable=parent / executable_name,
            _version=packaging.version.Version(version),
            _interpreter=parent / executable_name,
        )
        mocker.patch(
            "findpython.PythonVersion.implementation",
            new_callable=PropertyMock,
            return_value=platform.python_implementation(),
        )
        mocked_pythons.append(python)
        mocked_pythons_version_map[version] = python

        if make_system:
            mocker.patch(
                "poetry.utils.env.python.Python.get_system_python",
                return_value=Python(python=python),
            )
            mocked_pythons_version_map[""] = python

        return Python(python=python)

    return register


@pytest.fixture
def without_mocked_findpython(
    mock_findpython_find: MagicMock,
    mock_findpython_find_all: MagicMock,
    mocker: MockerFixture,
) -> None:
    """
    This fixture stops the mocks for the functions `mock_findpython_find_all`
    and `mock_findpython_find`. It is intended for use within unit tests
    to ensure that the actual behavior of the mocked functions is not
    included unless explicitly required.
    """
    mocker.stop(mock_findpython_find_all)
    mocker.stop(mock_findpython_find)


@pytest.fixture(autouse=True)
def with_mocked_findpython(
    mock_findpython_find: MagicMock,
    mock_findpython_find_all: MagicMock,
) -> None:
    """
    Fixture that mocks the `findpython` library functions `find` and `find_all`.

    This fixture enables controlled testing of Python version discovery by providing
    mocked data for `findpython.PythonVersion` objects and behavior. It patches
    the `findpython.find` and `findpython.find_all` methods using the given mock
    data to simulate real functionality.

    This function mock behavior includes:
    - Finding Python versions by an exact match of executable name or selectable from
      candidates whose executable names end with the provided input.
    - Returning all mocked Python versions through the `findpython.find_all`.

    See also the `without_mocked_findpython`, `mocked_python_register`, `mock_findpython_find`,
    and `mock_findpython_find_all` fixtures.
    """
    return


@pytest.fixture
def with_no_active_python(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "poetry.utils.env.python.Python.get_active_python",
        return_value=None,
    )
