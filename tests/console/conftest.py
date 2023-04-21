from __future__ import annotations

import os

from typing import TYPE_CHECKING

import pytest

from cleo.io.null_io import NullIO
from cleo.testers.application_tester import ApplicationTester
from cleo.testers.command_tester import CommandTester

from poetry.installation import Installer
from poetry.utils.env import MockEnv
from tests.helpers import MOCK_DEFAULT_GIT_REVISION
from tests.helpers import PoetryTestApplication
from tests.helpers import TestExecutor
from tests.helpers import mock_clone


if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from pytest_mock import MockerFixture

    from poetry.installation.executor import Executor
    from poetry.poetry import Poetry
    from poetry.repositories import Repository
    from poetry.utils.env import Env
    from tests.conftest import Config
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture
def env(tmp_path: Path) -> MockEnv:
    path = tmp_path / ".venv"
    path.mkdir(parents=True)
    return MockEnv(path=path, is_venv=True)


@pytest.fixture(autouse=True)
def setup(
    mocker: MockerFixture,
    installed: Repository,
    config: Config,
    env: MockEnv,
) -> Iterator[None]:
    # Do not run pip commands of the executor
    mocker.patch("poetry.installation.executor.Executor.run_pip")

    p = mocker.patch("poetry.installation.installer.Installer._get_installed")
    p.return_value = installed

    p = mocker.patch(
        "poetry.repositories.installed_repository.InstalledRepository.load"
    )
    p.return_value = installed

    # Patch git module to not actually clone projects
    mocker.patch("poetry.vcs.git.Git.clone", new=mock_clone)
    p = mocker.patch("poetry.vcs.git.Git.get_revision")
    p.return_value = MOCK_DEFAULT_GIT_REVISION

    # Patch the virtual environment creation do actually do nothing
    mocker.patch("poetry.utils.env.EnvManager.create_venv", return_value=env)

    # Patch the virtual environment creation do actually do nothing
    mocker.patch("poetry.utils.env.EnvManager.create_venv", return_value=env)

    # Setting terminal width
    environ = dict(os.environ)
    os.environ["COLUMNS"] = "80"

    yield

    os.environ.clear()
    os.environ.update(environ)


@pytest.fixture
def project_directory() -> str:
    return "simple_project"


@pytest.fixture
def poetry(
    project_directory: str,
    project_factory: ProjectFactory,
    fixture_dir: FixtureDirGetter,
) -> Poetry:
    return project_factory(name="simple", source=fixture_dir(project_directory))


@pytest.fixture
def app(poetry: Poetry) -> PoetryTestApplication:
    app_ = PoetryTestApplication(poetry)
    app_._load_plugins()
    return app_


@pytest.fixture
def app_tester(app: PoetryTestApplication) -> ApplicationTester:
    return ApplicationTester(app)


@pytest.fixture()
def executor(poetry: Poetry, config: Config, env: MockEnv) -> TestExecutor:
    return TestExecutor(env, poetry.pool, config, NullIO())


@pytest.fixture
def command_tester_factory(
    app: PoetryTestApplication, env: MockEnv
) -> CommandTesterFactory:
    def _tester(
        command: str,
        poetry: Poetry | None = None,
        installer: Installer | None = None,
        executor: Executor | None = None,
        environment: Env | None = None,
    ) -> CommandTester:
        command_obj = app.find(command)
        tester = CommandTester(command_obj)

        # Setting the formatter from the application
        # TODO: Find a better way to do this in Cleo
        app_io = app.create_io()
        formatter = app_io.output.formatter
        tester.io.output.set_formatter(formatter)
        tester.io.error_output.set_formatter(formatter)

        if poetry:
            app._poetry = poetry

        poetry = app.poetry

        if hasattr(command_obj, "set_env"):
            command_obj.set_env(environment or env)

        if hasattr(command_obj, "set_installer"):
            installer = installer or Installer(
                tester.io,
                env,
                poetry.package,
                poetry.locker,
                poetry.pool,
                poetry.config,
                executor=executor
                or TestExecutor(env, poetry.pool, poetry.config, tester.io),
            )
            command_obj.set_installer(installer)

        return tester

    return _tester


@pytest.fixture
def do_lock(command_tester_factory: CommandTesterFactory, poetry: Poetry) -> None:
    command_tester_factory("lock").execute()
    assert poetry.locker.lock.exists()
