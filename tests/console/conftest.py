import os
import re

import pytest

from cleo import ApplicationTester

from poetry.console import Application as BaseApplication
from poetry.core.masonry.utils.helpers import escape_name
from poetry.core.masonry.utils.helpers import escape_version
from poetry.core.packages.utils.link import Link
from poetry.factory import Factory
from poetry.installation.executor import Executor as BaseExecutor
from poetry.installation.noop_installer import NoopInstaller
from poetry.io.null_io import NullIO
from poetry.packages import Locker as BaseLocker
from poetry.poetry import Poetry as BasePoetry
from poetry.repositories import Pool
from poetry.repositories import Repository as BaseRepository
from poetry.repositories.exceptions import PackageNotFound
from poetry.utils._compat import Path
from poetry.utils.env import MockEnv
from poetry.utils.toml_file import TomlFile
from tests.helpers import mock_clone


class Executor(BaseExecutor):
    def __init__(self, *args, **kwargs):
        super(Executor, self).__init__(*args, **kwargs)

        self._installs = []
        self._updates = []
        self._uninstalls = []

    @property
    def installations(self):
        return self._installs

    @property
    def updates(self):
        return self._updates

    @property
    def removals(self):
        return self._uninstalls

    def _do_execute_operation(self, operation):
        super(Executor, self)._do_execute_operation(operation)

        if not operation.skipped:
            getattr(self, "_{}s".format(operation.job_type)).append(operation.package)

    def _execute_install(self, operation):
        return 0

    def _execute_update(self, operation):
        return 0

    def _execute_remove(self, operation):
        return 0


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


class Application(BaseApplication):
    def __init__(self, poetry):
        super(Application, self).__init__()

        self._poetry = poetry

    def reset_poetry(self):
        poetry = self._poetry
        self._poetry = Factory().create_poetry(self._poetry.file.path.parent)
        self._poetry.set_pool(poetry.pool)
        self._poetry.set_config(poetry.config)
        self._poetry.set_locker(poetry.locker)


class Locker(BaseLocker):
    def __init__(self, lock, local_config):
        self._lock = TomlFile(lock)
        self._local_config = local_config
        self._lock_data = None
        self._content_hash = self._get_content_hash()
        self._locked = False
        self._lock_data = None
        self._write = False

    def write(self, write=True):
        self._write = write

    def is_locked(self):
        return self._locked

    def locked(self, is_locked=True):
        self._locked = is_locked

        return self

    def mock_lock_data(self, data):
        self.locked()

        self._lock_data = data

    def is_fresh(self):
        return True

    def _write_lock_data(self, data):
        if self._write:
            super(Locker, self)._write_lock_data(data)
            self._locked = True
            return

        self._lock_data = None


class Poetry(BasePoetry):
    def __init__(self, file, local_config, package, locker, config):
        self._file = TomlFile(file)
        self._package = package
        self._local_config = local_config
        self._locker = Locker(locker.lock.path, locker._local_config)
        self._config = config

        # Configure sources
        self._pool = Pool()


class Repository(BaseRepository):
    def find_packages(
        self, name, constraint=None, extras=None, allow_prereleases=False
    ):
        packages = super(Repository, self).find_packages(
            name, constraint, extras, allow_prereleases
        )
        if len(packages) == 0:
            raise PackageNotFound("Package [{}] not found.".format(name))
        return packages

    def find_links_for_package(self, package):
        return [
            Link(
                "https://foo.bar/files/{}-{}-py2.py3-none-any.whl".format(
                    escape_name(package.name), escape_version(package.version.text)
                )
            )
        ]


@pytest.fixture
def repo(http):
    http.register_uri(
        http.GET,
        re.compile("^https?://foo.bar/(.+?)$"),
    )
    return Repository(name="foo")


@pytest.fixture
def project_directory():
    return "simple_project"


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
