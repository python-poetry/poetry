import os

from pathlib import Path
<<<<<<< HEAD
from typing import TYPE_CHECKING
from typing import Iterator
=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

import pytest

from cleo.io.null_io import NullIO
from cleo.testers.application_tester import ApplicationTester

from poetry.factory import Factory
from poetry.installation.noop_installer import NoopInstaller
from poetry.repositories import Pool
from poetry.utils.env import MockEnv
<<<<<<< HEAD
from tests.helpers import PoetryTestApplication
=======
from tests.helpers import TestApplication
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
from tests.helpers import TestExecutor
from tests.helpers import TestLocker
from tests.helpers import mock_clone


<<<<<<< HEAD
if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from poetry.repositories import Repository
    from tests.conftest import Config
    from tests.helpers import TestRepository


@pytest.fixture()
def installer() -> NoopInstaller:
=======
@pytest.fixture()
def installer():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return NoopInstaller()


@pytest.fixture
<<<<<<< HEAD
def env(tmp_dir: str) -> MockEnv:
=======
def env(tmp_dir):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    path = Path(tmp_dir) / ".venv"
    path.mkdir(parents=True)
    return MockEnv(path=path, is_venv=True)


@pytest.fixture(autouse=True)
<<<<<<< HEAD
def setup(
    mocker: "MockerFixture",
    installer: NoopInstaller,
    installed: "Repository",
    config: "Config",
    env: MockEnv,
) -> Iterator[None]:
=======
def setup(mocker, installer, installed, config, env):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    # Set Installer's installer
    p = mocker.patch("poetry.installation.installer.Installer._get_installer")
    p.return_value = installer

    # Do not run pip commands of the executor
    mocker.patch("poetry.installation.executor.Executor.run_pip")

    p = mocker.patch("poetry.installation.installer.Installer._get_installed")
    p.return_value = installed

    p = mocker.patch(
        "poetry.repositories.installed_repository.InstalledRepository.load"
    )
    p.return_value = installed

    # Patch git module to not actually clone projects
    mocker.patch("poetry.core.vcs.git.Git.clone", new=mock_clone)
    mocker.patch("poetry.core.vcs.git.Git.checkout", new=lambda *_: None)
    p = mocker.patch("poetry.core.vcs.git.Git.rev_parse")
    p.return_value = "9cf87a285a2d3fbb0b9fa621997b3acc3631ed24"

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
<<<<<<< HEAD
def project_directory() -> str:
=======
def project_directory():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return "simple_project"


@pytest.fixture
<<<<<<< HEAD
def poetry(
    repo: "TestRepository", project_directory: str, config: "Config"
) -> "Poetry":
=======
def poetry(repo, project_directory, config):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    p = Factory().create_poetry(
        Path(__file__).parent.parent / "fixtures" / project_directory
    )
    p.set_locker(TestLocker(p.locker.lock.path, p.locker._local_config))

    with p.file.path.open(encoding="utf-8") as f:
        content = f.read()

    p.set_config(config)

    pool = Pool()
    pool.add_repository(repo)
    p.set_pool(pool)

    yield p

    with p.file.path.open("w", encoding="utf-8") as f:
        f.write(content)


@pytest.fixture
<<<<<<< HEAD
def app(poetry: "Poetry") -> PoetryTestApplication:
    app_ = PoetryTestApplication(poetry)
=======
def app(poetry):
    app_ = TestApplication(poetry)
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

    return app_


@pytest.fixture
<<<<<<< HEAD
def app_tester(app: PoetryTestApplication) -> ApplicationTester:
=======
def app_tester(app):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return ApplicationTester(app)


@pytest.fixture
<<<<<<< HEAD
def new_installer_disabled(config: "Config") -> None:
=======
def new_installer_disabled(config):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    config.merge({"experimental": {"new-installer": False}})


@pytest.fixture()
<<<<<<< HEAD
def executor(poetry: "Poetry", config: "Config", env: MockEnv) -> TestExecutor:
=======
def executor(poetry, config, env):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return TestExecutor(env, poetry.pool, config, NullIO())
