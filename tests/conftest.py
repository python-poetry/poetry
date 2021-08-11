import os
import re
import shutil
import sys
import tempfile

from pathlib import Path
from typing import Any
from typing import Dict

import httpretty
import pytest

from cleo.testers.command_tester import CommandTester
from keyring.backend import KeyringBackend

from poetry.config.config import Config as BaseConfig
from poetry.config.dict_config_source import DictConfigSource
from poetry.factory import Factory
from poetry.inspection.info import PackageInfo
from poetry.inspection.info import PackageInfoError
from poetry.installation import Installer
from poetry.layouts import layout
from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.utils.env import EnvManager
from poetry.utils.env import SystemEnv
from poetry.utils.env import VirtualEnv
from tests.helpers import TestExecutor
from tests.helpers import TestLocker
from tests.helpers import TestRepository
from tests.helpers import get_package
from tests.helpers import mock_clone
from tests.helpers import mock_download


class Config(BaseConfig):
    def get(self, setting_name: str, default: Any = None) -> Any:
        self.merge(self._config_source.config)
        self.merge(self._auth_config_source.config)

        return super(Config, self).get(setting_name, default=default)

    def raw(self) -> Dict[str, Any]:
        self.merge(self._config_source.config)
        self.merge(self._auth_config_source.config)

        return super(Config, self).raw()

    def all(self) -> Dict[str, Any]:
        self.merge(self._config_source.config)
        self.merge(self._auth_config_source.config)

        return super(Config, self).all()


class DummyBackend(KeyringBackend):
    def __init__(self):
        self._passwords = {}

    @classmethod
    def priority(cls):
        return 42

    def set_password(self, service, username, password):
        self._passwords[service] = {username: password}

    def get_password(self, service, username):
        return self._passwords.get(service, {}).get(username)

    def get_credential(self, service, username):
        return self._passwords.get(service, {}).get(username)

    def delete_password(self, service, username):
        if service in self._passwords and username in self._passwords[service]:
            del self._passwords[service][username]


@pytest.fixture()
def dummy_keyring():
    return DummyBackend()


@pytest.fixture()
def with_simple_keyring(dummy_keyring):
    import keyring

    keyring.set_keyring(dummy_keyring)


@pytest.fixture()
def with_fail_keyring():
    import keyring

    from keyring.backends.fail import Keyring

    keyring.set_keyring(Keyring())


@pytest.fixture()
def with_chained_keyring(mocker):
    from keyring.backends.fail import Keyring

    mocker.patch("keyring.backend.get_all_keyring", [Keyring()])
    import keyring

    from keyring.backends.chainer import ChainerBackend

    keyring.set_keyring(ChainerBackend())


@pytest.fixture
def config_cache_dir(tmp_dir):
    path = Path(tmp_dir) / ".cache" / "pypoetry"
    path.mkdir(parents=True)
    return path


@pytest.fixture
def config_virtualenvs_path(config_cache_dir):
    return config_cache_dir / "virtualenvs"


@pytest.fixture
def config_source(config_cache_dir):
    source = DictConfigSource()
    source.add_property("cache-dir", str(config_cache_dir))

    return source


@pytest.fixture
def auth_config_source():
    source = DictConfigSource()

    return source


@pytest.fixture
def config(config_source, auth_config_source, mocker):
    import keyring

    from keyring.backends.fail import Keyring

    keyring.set_keyring(Keyring())

    c = Config()
    c.merge(config_source.config)
    c.set_config_source(config_source)
    c.set_auth_config_source(auth_config_source)

    mocker.patch("poetry.factory.Factory.create_config", return_value=c)
    mocker.patch("poetry.config.config.Config.set_config_source")

    return c


@pytest.fixture(autouse=True)
def mock_user_config_dir(mocker):
    config_dir = tempfile.mkdtemp(prefix="poetry_config_")
    mocker.patch("poetry.locations.CONFIG_DIR", new=config_dir)
    mocker.patch("poetry.factory.CONFIG_DIR", new=config_dir)
    yield
    shutil.rmtree(config_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def download_mock(mocker):
    # Patch download to not download anything but to just copy from fixtures
    mocker.patch("poetry.utils.helpers.download_file", new=mock_download)
    mocker.patch("poetry.puzzle.provider.download_file", new=mock_download)
    mocker.patch("poetry.repositories.pypi_repository.download_file", new=mock_download)


@pytest.fixture(autouse=True)
def pep517_metadata_mock(mocker):
    @classmethod  # noqa
    def _pep517_metadata(cls, path):
        try:
            return PackageInfo.from_setup_files(path)
        except PackageInfoError:
            pass
        return PackageInfo(name="demo", version="0.1.2")

    mocker.patch(
        "poetry.inspection.info.PackageInfo._pep517_metadata",
        _pep517_metadata,
    )


@pytest.fixture
def environ():
    original_environ = dict(os.environ)

    yield

    os.environ.clear()
    os.environ.update(original_environ)


@pytest.fixture(autouse=True)
def git_mock(mocker):
    # Patch git module to not actually clone projects
    mocker.patch("poetry.core.vcs.git.Git.clone", new=mock_clone)
    mocker.patch("poetry.core.vcs.git.Git.checkout", new=lambda *_: None)
    p = mocker.patch("poetry.core.vcs.git.Git.rev_parse")
    p.return_value = "9cf87a285a2d3fbb0b9fa621997b3acc3631ed24"


@pytest.fixture
def http():
    httpretty.reset()
    httpretty.enable(allow_net_connect=False)

    yield httpretty

    httpretty.activate()
    httpretty.reset()


@pytest.fixture
def fixture_base():
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_dir(fixture_base):
    def _fixture_dir(name):
        return fixture_base / name

    return _fixture_dir


@pytest.fixture
def tmp_dir():
    dir_ = tempfile.mkdtemp(prefix="poetry_")

    yield dir_

    shutil.rmtree(dir_)


@pytest.fixture
def mocked_open_files(mocker):
    files = []
    original = Path.open

    def mocked_open(self, *args, **kwargs):
        if self.name in {"pyproject.toml"}:
            return mocker.MagicMock()
        return original(self, *args, **kwargs)

    mocker.patch("pathlib.Path.open", mocked_open)

    yield files


@pytest.fixture
def tmp_venv(tmp_dir):
    venv_path = Path(tmp_dir) / "venv"

    EnvManager.build_venv(str(venv_path))

    venv = VirtualEnv(venv_path)
    yield venv

    shutil.rmtree(str(venv.path))


@pytest.fixture
def installed():
    return Repository()


@pytest.fixture(scope="session")
def current_env():
    return SystemEnv(Path(sys.executable))


@pytest.fixture(scope="session")
def current_python(current_env):
    return current_env.version_info[:3]


@pytest.fixture(scope="session")
def default_python(current_python):
    return "^{}".format(".".join(str(v) for v in current_python[:2]))


@pytest.fixture
def repo(http):
    http.register_uri(
        http.GET,
        re.compile("^https?://foo.bar/(.+?)$"),
    )
    return TestRepository(name="foo")


@pytest.fixture
def project_factory(tmp_dir, config, repo, installed, default_python):
    workspace = Path(tmp_dir)

    def _factory(
        name=None,
        dependencies=None,
        dev_dependencies=None,
        pyproject_content=None,
        poetry_lock_content=None,
        install_deps=True,
    ):
        project_dir = workspace / "poetry-fixture-{}".format(name)
        dependencies = dependencies or {}
        dev_dependencies = dev_dependencies or {}

        if pyproject_content:
            project_dir.mkdir(parents=True, exist_ok=True)
            with project_dir.joinpath("pyproject.toml").open(
                "w", encoding="utf-8"
            ) as f:
                f.write(pyproject_content)
        else:
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

        locker = TestLocker(
            poetry.locker.lock.path, poetry.locker._local_config
        )  # noqa
        locker.write()

        poetry.set_locker(locker)
        poetry.set_config(config)

        pool = Pool()
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
def command_tester_factory(app, env):
    def _tester(command, poetry=None, installer=None, executor=None, environment=None):
        command = app.find(command)
        tester = CommandTester(command)

        # Setting the formatter from the application
        # TODO: Find a better way to do this in Cleo
        app_io = app.create_io()
        formatter = app_io.output.formatter
        tester.io.output.set_formatter(formatter)
        tester.io.error_output.set_formatter(formatter)

        if poetry:
            app._poetry = poetry

        poetry = app.poetry
        command._pool = poetry.pool

        if hasattr(command, "set_env"):
            command.set_env(environment or env)

        if hasattr(command, "set_installer"):
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
            installer.use_executor(True)
            command.set_installer(installer)

        return tester

    return _tester


@pytest.fixture
def do_lock(command_tester_factory, poetry):
    command_tester_factory("lock").execute()
    assert poetry.locker.lock.exists()
