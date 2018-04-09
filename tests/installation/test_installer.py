from __future__ import unicode_literals

import sys

import pytest
import toml

from poetry.installation import Installer as BaseInstaller
from poetry.installation.noop_installer import NoopInstaller
from poetry.io import NullIO
from poetry.packages import Locker as BaseLocker
from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils._compat import Path
from poetry.utils._compat import PY2
from poetry.utils.venv import NullVenv

from tests.helpers import get_dependency
from tests.helpers import get_package


class Installer(BaseInstaller):

    def _get_installer(self):
        return NoopInstaller()


class CustomInstalledRepository(InstalledRepository):

    @classmethod
    def load(cls, venv):
        return cls()


class Locker(BaseLocker):

    def __init__(self):
        self._written_data = None
        self._locked = False
        self._content_hash = self._get_content_hash()
        
    @property
    def written_data(self):
        return self._written_data

    def locked(self, is_locked=True):
        self._locked = is_locked

        return self

    def mock_lock_data(self, data):
        self._lock_data = data

    def is_locked(self):
        return self._locked

    def is_fresh(self):
        return True

    def _get_content_hash(self):
        return '123456789'
    
    def _write_lock_data(self, data):
        for package in data['package']:
            python_versions = str(package['python-versions'])
            platform = str(package['platform'])
            if PY2:
                python_versions = python_versions.decode()
                platform = platform.decode()
                if 'requirements' in package:
                    requirements = {}
                    for key, value in package['requirements'].items():
                        requirements[key.decode()] = value.decode()

                    package['requirements'] = requirements

            package['python-versions'] = python_versions
            package['platform'] = platform
            if not package['dependencies']:
                del package['dependencies']

        self._written_data = data


@pytest.fixture(autouse=True)
def setup():
    # Mock python version and platform to get reliable tests
    original_platform = sys.platform

    sys.platform = 'darwin'

    yield

    sys.platform = original_platform


@pytest.fixture()
def package():
    return get_package('root', '1.0')


@pytest.fixture()
def repo():
    return Repository()


@pytest.fixture()
def pool(repo):
    pool = Pool()
    pool.add_repository(repo)

    return pool


@pytest.fixture()
def installed():
    return CustomInstalledRepository()


@pytest.fixture()
def locker():
    return Locker()


@pytest.fixture()
def venv():
    return NullVenv()


@pytest.fixture()
def installer(package, pool, locker, venv, installed):
    return Installer(NullIO(), venv, package, locker, pool, installed=installed)


def fixture(name):
    file = Path(__file__).parent / 'fixtures' / '{}.test'.format(name)

    with file.open() as f:
        return toml.loads(f.read())


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


def test_add_with_sub_dependencies(installer, locker, repo, package):
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.1')
    package_c = get_package('C', '1.2')
    package_d = get_package('D', '1.3')
    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    package.add_dependency('A', '~1.0')
    package.add_dependency('B', '^1.0')

    package_a.add_dependency('D', '^1.0')
    package_b.add_dependency('C', '~1.2')

    installer.run()
    expected = fixture('with-sub-dependencies')

    assert locker.written_data == expected


def test_run_with_python_versions(installer, locker, repo, package):
    package.python_versions = '~2.7 || ^3.4'

    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.1')
    package_c12 = get_package('C', '1.2')
    package_c12.python_versions = '~2.7 || ^3.6'
    package_c13 = get_package('C', '1.3')
    package_c13.python_versions = '~3.3'

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c12)
    repo.add_package(package_c13)

    package.add_dependency('A', '~1.0')
    package.add_dependency('B', '^1.0')
    package.add_dependency('C', '^1.0')

    installer.run()
    expected = fixture('with-python-versions')

    assert locker.written_data == expected


def test_run_with_optional_and_python_restricted_dependencies(installer, locker, repo, package):
    package.python_versions = '~2.7 || ^3.4'

    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.1')
    package_c12 = get_package('C', '1.2')
    package_c13 = get_package('C', '1.3')
    package_d = get_package('D', '1.4')
    package_c13.add_dependency('D', '^1.2')

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c12)
    repo.add_package(package_c13)
    repo.add_package(package_d)

    package.add_dependency('A', {'version': '~1.0', 'optional': True})
    package.add_dependency('B', {'version': '^1.0', 'python': '~2.4'})
    package.add_dependency('C', {'version': '^1.0', 'python': '~2.7 || ^3.4'})

    installer.run()
    expected = fixture('with-optional-dependencies')

    import json
    print(json.dumps(locker.written_data, indent=2, sort_keys=True))
    print(json.dumps(expected, indent=2, sort_keys=True))
    assert locker.written_data == expected

    installer = installer.installer
    # We should only have 2 installs:
    # C,D since python version is not compatible
    # with B's python constraint and A is optional
    assert len(installer.installs) == 2
    assert installer.installs[0].name == 'd'
    assert installer.installs[1].name == 'c'


def test_run_with_optional_and_platform_restricted_dependencies(installer, locker, repo, package):
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.1')
    package_c12 = get_package('C', '1.2')
    package_c13 = get_package('C', '1.3')
    package_d = get_package('D', '1.4')
    package_c13.add_dependency('D', '^1.2')

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c12)
    repo.add_package(package_c13)
    repo.add_package(package_d)

    package.add_dependency('A', {'version': '~1.0', 'optional': True})
    package.add_dependency('B', {'version': '^1.0', 'platform': 'custom'})
    package.add_dependency('C', {'version': '^1.0', 'platform': 'darwin'})

    installer.run()
    expected = fixture('with-platform-dependencies')

    assert locker.written_data == expected

    installer = installer.installer
    # We should only have 2 installs:
    # C,D since the mocked python version is not compatible
    # with B's python constraint and A is optional
    assert len(installer.installs) == 2
    assert installer.installs[0].name == 'd'
    assert installer.installs[1].name == 'c'


def test_run_with_dependencies_extras(installer, locker, repo, package):
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    package_c = get_package('C', '1.0')

    package_b.extras = {
        'foo': [get_dependency('C', '^1.0')]
    }

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    package.add_dependency('A', '^1.0')
    package.add_dependency('B', {'version': '^1.0', 'extras': ['foo']})

    installer.run()
    expected = fixture('with-dependencies-extras')

    assert locker.written_data == expected


def test_run_does_not_install_extras_if_not_requested(installer, locker, repo, package):
    package.extras['foo'] = [
        get_dependency('D')
    ]
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    package_c = get_package('C', '1.0')
    package_d = get_package('D', '1.1')

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    package.add_dependency('A', '^1.0')
    package.add_dependency('B', '^1.0')
    package.add_dependency('C', '^1.0')
    package.add_dependency('D', {'version': '^1.0', 'optional': True})

    installer.run()
    expected = fixture('extras')

    # Extras are pinned in lock
    assert locker.written_data == expected

    # But should not be installed
    installer = installer.installer
    assert len(installer.installs) == 3  # A, B, C


def test_run_installs_extras_if_requested(installer, locker, repo, package):
    package.extras['foo'] = [
        get_dependency('D')
    ]
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    package_c = get_package('C', '1.0')
    package_d = get_package('D', '1.1')

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    package.add_dependency('A', '^1.0')
    package.add_dependency('B', '^1.0')
    package.add_dependency('C', '^1.0')
    package.add_dependency('D', {'version': '^1.0', 'optional': True})

    installer.extras(['foo'])
    installer.run()
    expected = fixture('extras')

    # Extras are pinned in lock
    assert locker.written_data == expected

    # But should not be installed
    installer = installer.installer
    assert len(installer.installs) == 4  # A, B, C, D


def test_run_installs_extras_with_deps_if_requested(installer, locker, repo, package):
    package.extras['foo'] = [
        get_dependency('C')
    ]
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    package_c = get_package('C', '1.0')
    package_d = get_package('D', '1.1')

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    package.add_dependency('A', '^1.0')
    package.add_dependency('B', '^1.0')
    package.add_dependency('C', {'version': '^1.0', 'optional': True})

    package_c.add_dependency('D', '^1.0')

    installer.extras(['foo'])
    installer.run()
    expected = fixture('extras-with-dependencies')

    # Extras are pinned in lock
    assert locker.written_data == expected

    # But should not be installed
    installer = installer.installer
    assert len(installer.installs) == 4  # A, B, C, D


def test_run_installs_extras_with_deps_if_requested_locked(installer, locker, repo, package):
    locker.locked(True)
    locker.mock_lock_data(fixture('extras-with-dependencies'))
    package.extras['foo'] = [
        get_dependency('C')
    ]
    package_a = get_package('A', '1.0')
    package_b = get_package('B', '1.0')
    package_c = get_package('C', '1.0')
    package_d = get_package('D', '1.1')

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    package.add_dependency('A', '^1.0')
    package.add_dependency('B', '^1.0')
    package.add_dependency('C', {'version': '^1.0', 'optional': True})

    package_c.add_dependency('D', '^1.0')

    installer.extras(['foo'])
    installer.run()

    # But should not be installed
    installer = installer.installer
    assert len(installer.installs) == 4  # A, B, C, D

