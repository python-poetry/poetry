import os

import pytest

from keyring.backend import KeyringBackend

from poetry.utils.password_manager import KeyRing
from poetry.utils.password_manager import KeyRingError
from poetry.utils.password_manager import PasswordManager


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

    def delete_password(self, service, username):
        if service in self._passwords and username in self._passwords[service]:
            del self._passwords[service][username]


@pytest.fixture()
def backend():
    return DummyBackend()


@pytest.fixture()
def mock_available_backend(backend):
    import keyring

    keyring.set_keyring(backend)


@pytest.fixture()
def mock_unavailable_backend():
    import keyring
    from keyring.backends.fail import Keyring

    keyring.set_keyring(Keyring())


@pytest.fixture()
def mock_chainer_backend(mocker):
    from keyring.backends.fail import Keyring

    mocker.patch("keyring.backend.get_all_keyring", [Keyring()])
    import keyring
    from keyring.backends.chainer import ChainerBackend

    keyring.set_keyring(ChainerBackend())


def test_set_http_password(config, mock_available_backend, backend):
    manager = PasswordManager(config)

    assert manager.keyring.is_available()
    manager.set_http_password("foo", "bar", "baz")

    assert "baz" == backend.get_password("poetry-repository-foo", "bar")

    auth = config.get("http-basic.foo")
    assert "bar" == auth["username"]
    assert "password" not in auth


def test_get_http_auth(config, mock_available_backend, backend):
    backend.set_password("poetry-repository-foo", "bar", "baz")
    config.auth_config_source.add_property("http-basic.foo", {"username": "bar"})
    manager = PasswordManager(config)

    assert manager.keyring.is_available()
    auth = manager.get_http_auth("foo")

    assert "bar" == auth["username"]
    assert "baz" == auth["password"]


def test_delete_http_password(config, mock_available_backend, backend):
    backend.set_password("poetry-repository-foo", "bar", "baz")
    config.auth_config_source.add_property("http-basic.foo", {"username": "bar"})
    manager = PasswordManager(config)

    assert manager.keyring.is_available()
    manager.delete_http_password("foo")

    assert backend.get_password("poetry-repository-foo", "bar") is None
    assert config.get("http-basic.foo") is None


def test_set_pypi_token(config, mock_available_backend, backend):
    manager = PasswordManager(config)

    assert manager.keyring.is_available()
    manager.set_pypi_token("foo", "baz")

    assert config.get("pypi-token.foo") is None

    assert "baz" == backend.get_password("poetry-repository-foo", "__token__")


def test_get_pypi_token(config, mock_available_backend, backend):
    backend.set_password("poetry-repository-foo", "__token__", "baz")
    manager = PasswordManager(config)

    assert manager.keyring.is_available()
    assert "baz" == manager.get_pypi_token("foo")


def test_delete_pypi_token(config, mock_available_backend, backend):
    backend.set_password("poetry-repository-foo", "__token__", "baz")
    manager = PasswordManager(config)

    assert manager.keyring.is_available()
    manager.delete_pypi_token("foo")

    assert backend.get_password("poetry-repository-foo", "__token__") is None


def test_set_http_password_with_unavailable_backend(config, mock_unavailable_backend):
    manager = PasswordManager(config)

    assert not manager.keyring.is_available()
    manager.set_http_password("foo", "bar", "baz")

    auth = config.get("http-basic.foo")
    assert "bar" == auth["username"]
    assert "baz" == auth["password"]


def test_get_http_auth_with_unavailable_backend(config, mock_unavailable_backend):
    config.auth_config_source.add_property(
        "http-basic.foo", {"username": "bar", "password": "baz"}
    )
    manager = PasswordManager(config)

    assert not manager.keyring.is_available()
    auth = manager.get_http_auth("foo")

    assert "bar" == auth["username"]
    assert "baz" == auth["password"]


def test_delete_http_password_with_unavailable_backend(
    config, mock_unavailable_backend
):
    config.auth_config_source.add_property(
        "http-basic.foo", {"username": "bar", "password": "baz"}
    )
    manager = PasswordManager(config)

    assert not manager.keyring.is_available()
    manager.delete_http_password("foo")

    assert config.get("http-basic.foo") is None


def test_set_pypi_token_with_unavailable_backend(config, mock_unavailable_backend):
    manager = PasswordManager(config)

    assert not manager.keyring.is_available()
    manager.set_pypi_token("foo", "baz")

    assert "baz" == config.get("pypi-token.foo")


def test_get_pypi_token_with_unavailable_backend(config, mock_unavailable_backend):
    config.auth_config_source.add_property("pypi-token.foo", "baz")
    manager = PasswordManager(config)

    assert not manager.keyring.is_available()
    assert "baz" == manager.get_pypi_token("foo")


def test_delete_pypi_token_with_unavailable_backend(config, mock_unavailable_backend):
    config.auth_config_source.add_property("pypi-token.foo", "baz")
    manager = PasswordManager(config)

    assert not manager.keyring.is_available()
    manager.delete_pypi_token("foo")

    assert config.get("pypi-token.foo") is None


def test_keyring_raises_errors_on_keyring_errors(mocker, mock_unavailable_backend):
    mocker.patch("poetry.utils.password_manager.KeyRing._check")

    key_ring = KeyRing("poetry")
    with pytest.raises(KeyRingError):
        key_ring.set_password("foo", "bar", "baz")

    with pytest.raises(KeyRingError):
        key_ring.get_password("foo", "bar")

    with pytest.raises(KeyRingError):
        key_ring.delete_password("foo", "bar")


def test_keyring_with_chainer_backend_and_not_compatible_only_should_be_unavailable(
    mock_chainer_backend,
):
    key_ring = KeyRing("poetry")

    assert not key_ring.is_available()


def test_get_http_auth_from_environment_variables(
    environ, config, mock_available_backend
):
    os.environ["POETRY_HTTP_BASIC_FOO_USERNAME"] = "bar"
    os.environ["POETRY_HTTP_BASIC_FOO_PASSWORD"] = "baz"

    manager = PasswordManager(config)

    auth = manager.get_http_auth("foo")

    assert "bar" == auth["username"]
    assert "baz" == auth["password"]
