from uuid import uuid4

import pytest

from keyring import get_keyring
from keyring import set_keyring
from keyring.backend import KeyringBackend
from keyring.errors import KeyringError

from poetry.utils.helpers import keyring_repository_password_del
from poetry.utils.helpers import keyring_repository_password_get
from poetry.utils.helpers import keyring_repository_password_set
from poetry.utils.helpers import keyring_service_name


class DictKeyring(KeyringBackend):
    priority = 1

    def __init__(self):
        self._storage = dict()

    def set_password(self, servicename, username, password):
        if servicename not in self._storage:
            self._storage[servicename] = dict()
        self._storage[servicename][username] = password

    def get_password(self, servicename, username):
        if servicename in self._storage:
            return self._storage[servicename].get(username)

    def delete_password(self, servicename, username):
        if servicename in self._storage:
            if username in self._storage[servicename]:
                del self._storage[servicename][username]
            if not self._storage[servicename]:
                del self._storage[servicename]


class BrokenKeyring(KeyringBackend):
    priority = 1

    def set_password(self, servicename, username, password):
        raise KeyringError()

    def get_password(self, servicename, username):
        raise KeyringError()

    def delete_password(self, servicename, username):
        raise KeyringError()


@pytest.fixture
def keyring():  # type: () -> KeyringBackend
    k = DictKeyring()
    set_keyring(k)
    return k


@pytest.fixture
def broken_keyring():  # type: () -> KeyringBackend
    k = BrokenKeyring()
    set_keyring(k)
    return k


@pytest.fixture
def repository():  # type: () -> str
    return "test"


@pytest.fixture
def username():  # type: () -> str
    return "username"


@pytest.fixture
def password():  # type: () -> str
    return str(uuid4())


def test_keyring_repository_password_get(keyring, repository, username, password):
    keyring.set_password(keyring_service_name(repository), username, password)
    assert keyring_repository_password_get(repository, username) == password


def test_keyring_repository_password_get_not_set(keyring, repository, username):
    assert keyring.get_password(keyring_service_name(repository), username) is None
    assert keyring_repository_password_get(repository, username) is None


def test_keyring_repository_password_get_broken(broken_keyring):
    assert get_keyring() == broken_keyring
    assert keyring_repository_password_get("repository", "username") is None


def test_keyring_repository_password_set(keyring, repository, username, password):
    keyring_repository_password_set(repository, username, password)
    assert keyring.get_password(keyring_service_name(repository), username) == password


def test_keyring_repository_password_set_broken(broken_keyring):
    assert get_keyring() == broken_keyring

    with pytest.raises(RuntimeError):
        keyring_repository_password_set(repository, "username", "password")


def test_keyring_repository_password_del(
    keyring, config, repository, username, password
):
    keyring.set_password(keyring_service_name(repository), username, password)
    config.merge({"http-basic": {repository: {"username": username}}})
    keyring_repository_password_del(config, repository)
    assert keyring.get_password(keyring_service_name(repository), username) is None


def test_keyring_repository_password_del_not_set(keyring, config, repository, username):
    config.merge({"http-basic": {repository: {"username": username}}})
    keyring_repository_password_del(config, repository)
    assert keyring.get_password(keyring_service_name(repository), username) is None


def test_keyring_repository_password_del_broken(broken_keyring, config):
    assert get_keyring() == broken_keyring
    keyring_repository_password_del(config, "repository")
