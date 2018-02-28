import pytest
import toml

from pathlib import Path

from poetry.installation import Installer as BaseInstaller
from poetry.installation.noop_installer import NoopInstaller
from poetry.io import NullIO
from poetry.packages import Locker as BaseLocker
from poetry.repositories import Repository

from tests.helpers import get_package


class Installer(BaseInstaller):

    def _get_installer(self):
        return NoopInstaller()


class Locker(BaseLocker):

    def __init__(self):
        self._written_data = None
        self._locked = False
        self._content_hash = self._get_content_hash()
        
    @property
    def written_data(self):
        return self._written_data

    def locked(self, is_locked=True) -> 'Locker':
        self._locked = is_locked

        return self

    def mock_lock_data(self, data) -> None:
        self._lock_data = data

    def is_locked(self) -> bool:
        return self._locked

    def _get_content_hash(self) -> str:
        return '123456789'
    
    def _write_lock_data(self, data) -> None:
        self._written_data = data


@pytest.fixture()
def package():
    return get_package('root', '1.0')


@pytest.fixture()
def repo():
    return Repository()


@pytest.fixture()
def locker():
    return Locker()


def fixture(name):
    file = Path(__file__).parent / 'fixtures' / f'{name}.test'

    return toml.loads(file.read_text())


@pytest.fixture()
def installer(package, repo, locker):
    return Installer(NullIO(), package, locker, repo)


def test_run_no_dependencies(installer, locker):
    installer.run()
    expected = fixture('no-dependencies')

    assert locker.written_data == expected


def test_run_with_dependencies(installer, locker, repo, package):
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.1')
    repo.add_package(package_a)
    repo.add_package(package_b)

    package.add_dependency('A', '~1.0')
    package.add_dependency('B', '^1.0')

    installer.run()
    expected = fixture('with-dependencies')

    assert locker.written_data == expected


def test_run_whitelist_add(installer, locker, repo, package):
    locker.locked(True)
    locker.mock_lock_data({
        'package': [{
            'name': 'A',
            'version': '1.0',
            'category': 'main',
            'optional': False,
            'platform': '*',
            'python-versions': '*',
            'checksum': []
        }],
        'metadata': {
            'python-versions': '*',
            'platform': '*',
            'content-hash': '123456789',
            'hashes': {
                'A': []
            }
        }
    })
    package_a = get_package('A', '1.0')
    package_a_new = get_package('A', '1.1')
    package_b = get_package('B', '1.1')
    repo.add_package(package_a)
    repo.add_package(package_a_new)
    repo.add_package(package_b)

    package.add_dependency('A', '~1.0')
    package.add_dependency('B', '^1.0')

    installer.update(True)
    installer.whitelist({'B': '^1.1'})

    installer.run()
    expected = fixture('with-dependencies')

    assert locker.written_data == expected


def test_run_whitelist_remove(installer, locker, repo, package):
    locker.locked(True)
    locker.mock_lock_data({
        'package': [{
            'name': 'A',
            'version': '1.0',
            'category': 'main',
            'optional': False,
            'platform': '*',
            'python-versions': '*',
            'checksum': []
        }, {
            'name': 'B',
            'version': '1.1',
            'category': 'main',
            'optional': False,
            'platform': '*',
            'python-versions': '*',
            'checksum': []
        }],
        'metadata': {
            'python-versions': '*',
            'platform': '*',
            'content-hash': '123456789',
            'hashes': {
                'A': [],
                'B': []
            }
        }
    })
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.1')
    repo.add_package(package_a)
    repo.add_package(package_b)

    package.add_dependency('A', '~1.0')

    installer.update(True)
    installer.whitelist({'B': '^1.1'})

    installer.run()
    expected = fixture('remove')

    assert locker.written_data == expected
