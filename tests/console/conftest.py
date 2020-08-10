import os
import re
import shutil

import pytest

from cleo import ApplicationTester
from cleo import CommandTester

from poetry.factory import Factory
from poetry.installation import Installer
from poetry.installation.noop_installer import NoopInstaller
from poetry.io.null_io import NullIO
from poetry.repositories import Pool
from poetry.repositories import Repository as BaseRepository
from poetry.utils._compat import Path
from poetry.utils.env import MockEnv
from tests.console.helpers import Application
from tests.console.helpers import Locker
from tests.console.helpers import Repository
from tests.helpers import Executor
from tests.helpers import fixture
from tests.helpers import mock_clone


@pytest.fixture()
def installer():
    return NoopInstaller()


@pytest.fixture
def installed():
    return BaseRepository()


@pytest.fixture
def env():
    return MockEnv(path=Path("/prefix"), base=Path("/base/prefix"), is_venv=True)


@pytest.fixture(autouse=True)
def setup(mocker, installer, installed, config, env):
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
def repo(http):
    http.register_uri(
        http.GET, re.compile("^https?://foo.bar/(.+?)$"),
    )
    return Repository(name="foo")


@pytest.fixture
def project_directory():
    return "simple_project"


@pytest.fixture
def make_poetry(tmp_dir, repo, config):
    def make_poetry_from_fixture_name(name):
        src = fixture(name)
        dst = Path(tmp_dir) / name
        shutil.copytree(src.as_posix(), dst.as_posix())

        poetry = Factory().create_poetry(dst)
        poetry.set_locker(Locker(poetry.locker.lock.path, poetry.locker._local_config))
        poetry.set_config(config)

        pool = Pool()
        pool.add_repository(repo)
        poetry.set_pool(pool)

        return poetry

    return make_poetry_from_fixture_name


@pytest.fixture
def make_installer_command_tester(config, executor, env):
    def make_tester(poetry, command, app=None):
        if app is None:
            app = Application(poetry)
            app.config.set_terminate_after_run(False)

        tester = CommandTester(app.find(command))

        executor._io = tester.io

        installer = Installer(
            tester.io,
            env,
            poetry.package,
            poetry.locker,
            poetry.pool,
            config,
            executor=executor,
        )
        installer.use_executor(True)
        tester._command.set_installer(installer)
        tester._command.set_env(env)

        return tester

    yield make_tester


@pytest.fixture
def poetry(repo, project_directory, config):
    p = Factory().create_poetry(
        Path(__file__).parent.parent / "fixtures" / project_directory
    )
    p.set_locker(Locker(p.locker.lock.path, p.locker._local_config))

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
def app(poetry):
    app_ = Application(poetry)
    app_.config.set_terminate_after_run(False)

    return app_


@pytest.fixture
def app_tester(app):
    return ApplicationTester(app)


@pytest.fixture
def new_installer_disabled(config):
    config.merge({"experimental": {"new-installer": False}})


@pytest.fixture()
def executor(poetry, config, env):
    return Executor(env, poetry.pool, config, NullIO())
