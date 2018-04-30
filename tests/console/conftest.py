import pytest

from poetry.config import Config as BaseConfig
from poetry.console import Application as BaseApplication
from poetry.installation.noop_installer import NoopInstaller
from poetry.poetry import Poetry as BasePoetry
from poetry.packages import Locker as BaseLocker
from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.utils._compat import Path
from poetry.utils.toml_file import TomlFile
from poetry.utils.toml_file import TOMLFile


@pytest.fixture()
def installer():
    return NoopInstaller()


@pytest.fixture(autouse=True)
def setup(mocker, installer):
    # Set Installer's installer
    p = mocker.patch('poetry.installation.installer.Installer._get_installer')
    p.return_value = installer

    p = mocker.patch('poetry.installation.installer.Installer._get_installed')
    p.return_value = Repository()


class Application(BaseApplication):

    def __init__(self, poetry):
        super(Application, self).__init__()

        self._poetry = poetry

    def reset_poetry(self):
        poetry = self._poetry
        self._poetry = Poetry.create(self._poetry.file.path.parent)
        self._poetry._pool = poetry.pool


class Config(BaseConfig):

    def __init__(self, _):
        self._raw_content = {}
        self._content = TOMLFile([])


class Locker(BaseLocker):

    def __init__(self, lock, local_config):
        self._lock = TomlFile(lock)
        self._local_config = local_config
        self._lock_data = None
        self._content_hash = self._get_content_hash()


class Poetry(BasePoetry):

    def __init__(self,
                 file,
                 local_config,
                 package,
                 locker
                 ):
        self._file = TomlFile(file)
        self._package = package
        self._local_config = local_config
        self._locker = Locker(locker.lock.path, locker._local_config)
        self._config = Config.create('config.toml')

        # Configure sources
        self._pool = Pool()


@pytest.fixture
def repo():
    return Repository()


@pytest.fixture
def poetry(repo):
    p = Poetry.create(
        Path(__file__).parent.parent / 'fixtures' / 'simple_project'
    )

    with p.file.path.open() as f:
        content = f.read()

    p.pool.remove_repository('pypi')
    p.pool.add_repository(repo)

    yield p

    with p.file.path.open('w') as f:
        f.write(content)


@pytest.fixture
def app(poetry):
    return Application(poetry)
