import os

from typing import TYPE_CHECKING

import pytest

from poetry.utils.password_manager import KeyRing
from poetry.utils.password_manager import KeyRingError
from poetry.utils.password_manager import PasswordManager


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tests.conftest import Config
    from tests.conftest import DummyBackend


def test_set_http_password(
    config: "Config", with_simple_keyring: None, dummy_keyring: "DummyBackend"
):
    manager = PasswordManager(config)

    assert manager.keyring.is_available()
    manager.set_http_password("foo", "bar", "baz")

    assert dummy_keyring.get_password("poetry-repository-foo", "bar") == "baz"

    auth = config.get("http-basic.foo")
    assert auth["username"] == "bar"
    assert "password" not in auth


def test_get_http_auth(
    config: "Config", with_simple_keyring: None, dummy_keyring: "DummyBackend"
):
    dummy_keyring.set_password("poetry-repository-foo", "bar", "baz")
    config.auth_config_source.add_property("http-basic.foo", {"username": "bar"})
    manager = PasswordManager(config)

    assert manager.keyring.is_available()
    auth = manager.get_http_auth("foo")

    assert auth["username"] == "bar"
    assert auth["password"] == "baz"


def test_delete_http_password(
    config: "Config", with_simple_keyring: None, dummy_keyring: "DummyBackend"
):
    dummy_keyring.set_password("poetry-repository-foo", "bar", "baz")
    config.auth_config_source.add_property("http-basic.foo", {"username": "bar"})
    manager = PasswordManager(config)

    assert manager.keyring.is_available()
    manager.delete_http_password("foo")

    assert dummy_keyring.get_password("poetry-repository-foo", "bar") is None
    assert config.get("http-basic.foo") is None


def test_set_pypi_token(
    config: "Config", with_simple_keyring: None, dummy_keyring: "DummyBackend"
):
    manager = PasswordManager(config)

    assert manager.keyring.is_available()
    manager.set_pypi_token("foo", "baz")

    assert config.get("pypi-token.foo") is None

    assert dummy_keyring.get_password("poetry-repository-foo", "__token__") == "baz"


def test_get_pypi_token(
    config: "Config", with_simple_keyring: None, dummy_keyring: "DummyBackend"
):
    dummy_keyring.set_password("poetry-repository-foo", "__token__", "baz")
    manager = PasswordManager(config)

    assert manager.keyring.is_available()
    assert manager.get_pypi_token("foo") == "baz"


def test_delete_pypi_token(
    config: "Config", with_simple_keyring: None, dummy_keyring: "DummyBackend"
):
    dummy_keyring.set_password("poetry-repository-foo", "__token__", "baz")
    manager = PasswordManager(config)

    assert manager.keyring.is_available()
    manager.delete_pypi_token("foo")

    assert dummy_keyring.get_password("poetry-repository-foo", "__token__") is None


def test_set_http_password_with_unavailable_backend(
    config: "Config", with_fail_keyring: None
):
    manager = PasswordManager(config)

    assert not manager.keyring.is_available()
    manager.set_http_password("foo", "bar", "baz")

    auth = config.get("http-basic.foo")
    assert auth["username"] == "bar"
    assert auth["password"] == "baz"


def test_get_http_auth_with_unavailable_backend(
    config: "Config", with_fail_keyring: None
):
    config.auth_config_source.add_property(
        "http-basic.foo", {"username": "bar", "password": "baz"}
    )
    manager = PasswordManager(config)

    assert not manager.keyring.is_available()
    auth = manager.get_http_auth("foo")

    assert auth["username"] == "bar"
    assert auth["password"] == "baz"


def test_delete_http_password_with_unavailable_backend(
    config: "Config", with_fail_keyring: None
):
    config.auth_config_source.add_property(
        "http-basic.foo", {"username": "bar", "password": "baz"}
    )
    manager = PasswordManager(config)

    assert not manager.keyring.is_available()
    manager.delete_http_password("foo")

    assert config.get("http-basic.foo") is None


def test_set_pypi_token_with_unavailable_backend(
    config: "Config", with_fail_keyring: None
):
    manager = PasswordManager(config)

    assert not manager.keyring.is_available()
    manager.set_pypi_token("foo", "baz")

    assert config.get("pypi-token.foo") == "baz"


def test_get_pypi_token_with_unavailable_backend(
    config: "Config", with_fail_keyring: None
):
    config.auth_config_source.add_property("pypi-token.foo", "baz")
    manager = PasswordManager(config)

    assert not manager.keyring.is_available()
    assert manager.get_pypi_token("foo") == "baz"


def test_delete_pypi_token_with_unavailable_backend(
    config: "Config", with_fail_keyring: None
):
    config.auth_config_source.add_property("pypi-token.foo", "baz")
    manager = PasswordManager(config)

    assert not manager.keyring.is_available()
    manager.delete_pypi_token("foo")

    assert config.get("pypi-token.foo") is None


def test_keyring_raises_errors_on_keyring_errors(
    mocker: "MockerFixture", with_fail_keyring: None
):
    mocker.patch("poetry.utils.password_manager.KeyRing._check")

    key_ring = KeyRing("poetry")
    with pytest.raises(KeyRingError):
        key_ring.set_password("foo", "bar", "baz")

    with pytest.raises(KeyRingError):
        key_ring.get_password("foo", "bar")

    with pytest.raises(KeyRingError):
        key_ring.delete_password("foo", "bar")


def test_keyring_with_chainer_backend_and_not_compatible_only_should_be_unavailable(
    with_chained_keyring: None,
):
    key_ring = KeyRing("poetry")

    assert not key_ring.is_available()


def test_get_http_auth_from_environment_variables(
    environ: None, config: "Config", with_simple_keyring: None
):
    os.environ["POETRY_HTTP_BASIC_FOO_USERNAME"] = "bar"
    os.environ["POETRY_HTTP_BASIC_FOO_PASSWORD"] = "baz"

    manager = PasswordManager(config)

    auth = manager.get_http_auth("foo")

    assert auth["username"] == "bar"
    assert auth["password"] == "baz"
