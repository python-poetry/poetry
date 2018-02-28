import json

import poetry.packages

from hashlib import sha256
from pathlib import Path
from typing import List

from poetry.repositories import Repository
from poetry.utils.toml_file import TomlFile


class Locker:

    _relevant_keys = [
        'name',
        'version',
        'python_versions',
        'dependencies',
        'dev-dependencies',
    ]

    def __init__(self, lock: Path, original: Path):
        self._lock = TomlFile(lock)
        self._original = TomlFile(original)
        self._lock_data = None
        self._content_hash = self._get_content_hash()

    @property
    def original(self) -> TomlFile:
        return self._original

    @property
    def lock(self) -> TomlFile:
        return self._lock

    @property
    def lock_data(self):
        if self._lock_data is None:
            self._lock_data = self._get_lock_data()

        return self._lock_data

    def is_locked(self) -> bool:
        """
        Checks whether the locker has been locked (lockfile found).
        """
        if not self._lock.exists():
            return False

        return 'packages' in self.lock_data

    def is_fresh(self) -> bool:
        """
        Checks whether the lock file is still up to date with the current hash.
        """
        lock = self._lock.read()

        if 'content-hash' in lock:
            return self._content_hash == lock['content-hash']

        return False

    def locked_repository(self, with_dev_reqs: bool = False) -> Repository:
        """
        Searches and returns a repository of locked packages.
        """
        if not self.is_locked():
            return Repository()

        lock_data = self.lock_data
        packages = Repository()

        if with_dev_reqs:
            locked_packages = lock_data['packages']
        else:
            locked_packages = [
                p for p in lock_data['packages'] if p['category'] == 'main'
            ]

        if not locked_packages:
            return packages

        for info in locked_packages:
            package = poetry.packages.Package(
                info['name'],
                info['version'],
                info['version']
            )
            package.category = info['category']
            package.optional = info['optional']
            package.hashes = info['checksum']
            package.python_versions = info['python-versions']

            packages.add_package(package)

        return packages

    def set_lock_data(self,
                      root, packages) -> bool:
        lock = {
            'root': {
                'name': root.name,
                'version': root.version,
                'python_versions': root.python_versions,
                'platform': root.platform
            },
            'packages': self._lock_packages(packages),
            'metadata': {
                'content-hash': self._content_hash
            }
        }

        if not self.is_locked() or lock != self.lock_data:
            self._lock.write(lock)
            self._lock_data = None

            return True

        return False

    def _get_content_hash(self) -> str:
        """
        Returns the sha256 hash of the sorted content of the composer file.
        """
        content = self._original.read()

        relevant_content = {}

        package = content['package']
        for key in ['name', 'version', 'python-versions', 'platform']:
            relevant_content[key] = package.get(key, '')

        for key in ['dependencies', 'dev-dependencies']:
            relevant_content[key] = content[key]

        content_hash = sha256(
            json.dumps(relevant_content, sort_keys=True).encode()
        ).hexdigest()

        return content_hash

    def _get_lock_data(self) -> dict:
        if not self._lock.exists():
            raise RuntimeError(
                'No lockfile found. Unable to read locked packages'
            )

        return self._lock.read()

    def _lock_packages(self, packages: List['poetry.packages.Package']) -> list:
        locked = []

        for package in sorted(packages, key=lambda x: x.name):
            spec = self._dump_package(package)

            locked.append(spec)

        return locked

    def _dump_package(self, package: 'poetry.packages.Package') -> dict:
        data = {
            'name': package.pretty_name,
            'version': package.pretty_version,
            'category': package.category,
            'optional': package.optional,
            'python-versions': package.python_versions,
            'platform': package.platform,
            'checksum': package.hashes
        }

        return data

