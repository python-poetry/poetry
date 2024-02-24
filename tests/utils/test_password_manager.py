from __future__ import annotations

import logging
import os

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from poetry.utils.password_manager import PasswordManager
from poetry.utils.password_manager import PoetryKeyring
from poetry.utils.password_manager import PoetryKeyringError


if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture
    from pytest_mock import MockerFixture

    from tests.conftest import Config
    from tests.conftest import DummyBackend


def test_set_http_password(
    config: Config, with_simple_keyring: None, dummy_keyring: DummyBackend
) -> None:
    manager = PasswordManager(config)

    assert PoetryKeyring.is_available()
    manager.set_http_password("foo", "bar", "baz")

    assert dummy_keyring.get_password("poetry-repository-foo", "bar") == "baz"

    auth = config.get("http-basic.foo")
    assert auth["username"] == "bar"
    assert "password" not in auth


def test_get_http_auth(
    config: Config, with_simple_keyring: None, dummy_keyring: DummyBackend
) -> None:
    dummy_keyring.set_password("poetry-repository-foo", "bar", "baz")
    config.auth_config_source.add_property("http-basic.foo", {"username": "bar"})
    manager = PasswordManager(config)

    assert PoetryKeyring.is_available()
    auth = manager.get_http_auth("foo")
    assert auth is not None

    assert auth["username"] == "bar"
    assert auth["password"] == "baz"


def test_delete_http_password(
    config: Config, with_simple_keyring: None, dummy_keyring: DummyBackend
) -> None:
    dummy_keyring.set_password("poetry-repository-foo", "bar", "baz")
    config.auth_config_source.add_property("http-basic.foo", {"username": "bar"})
    manager = PasswordManager(config)

    assert PoetryKeyring.is_available()
    manager.delete_http_password("foo")

    assert dummy_keyring.get_password("poetry-repository-foo", "bar") is None
    assert config.get("http-basic.foo") is None


def test_set_pypi_token(
    config: Config, with_simple_keyring: None, dummy_keyring: DummyBackend
) -> None:
    manager = PasswordManager(config)

    assert PoetryKeyring.is_available()
    manager.set_pypi_token("foo", "baz")

    assert config.get("pypi-token.foo") is None

    assert dummy_keyring.get_password("poetry-repository-foo", "__token__") == "baz"


def test_get_pypi_token(
    config: Config, with_simple_keyring: None, dummy_keyring: DummyBackend
) -> None:
    dummy_keyring.set_password("poetry-repository-foo", "__token__", "baz")
    manager = PasswordManager(config)

    assert PoetryKeyring.is_available()
    assert manager.get_pypi_token("foo") == "baz"


def test_delete_pypi_token(
    config: Config, with_simple_keyring: None, dummy_keyring: DummyBackend
) -> None:
    dummy_keyring.set_password("poetry-repository-foo", "__token__", "baz")
    manager = PasswordManager(config)

    assert PoetryKeyring.is_available()
    manager.delete_pypi_token("foo")

    assert dummy_keyring.get_password("poetry-repository-foo", "__token__") is None


def test_set_http_password_with_unavailable_backend(
    config: Config, with_fail_keyring: None
) -> None:
    manager = PasswordManager(config)

    assert not PoetryKeyring.is_available()
    manager.set_http_password("foo", "bar", "baz")

    auth = config.get("http-basic.foo")
    assert auth["username"] == "bar"
    assert auth["password"] == "baz"


def test_get_http_auth_with_unavailable_backend(
    config: Config, with_fail_keyring: None
) -> None:
    config.auth_config_source.add_property(
        "http-basic.foo", {"username": "bar", "password": "baz"}
    )
    manager = PasswordManager(config)

    assert not PoetryKeyring.is_available()
    auth = manager.get_http_auth("foo")
    assert auth is not None

    assert auth["username"] == "bar"
    assert auth["password"] == "baz"


def test_delete_http_password_with_unavailable_backend(
    config: Config, with_fail_keyring: None
) -> None:
    config.auth_config_source.add_property(
        "http-basic.foo", {"username": "bar", "password": "baz"}
    )
    manager = PasswordManager(config)

    assert not PoetryKeyring.is_available()
    manager.delete_http_password("foo")

    assert config.get("http-basic.foo") is None


def test_set_pypi_token_with_unavailable_backend(
    config: Config, with_fail_keyring: None
) -> None:
    manager = PasswordManager(config)

    assert not PoetryKeyring.is_available()
    manager.set_pypi_token("foo", "baz")

    assert config.get("pypi-token.foo") == "baz"


def test_get_pypi_token_with_unavailable_backend(
    config: Config, with_fail_keyring: None
) -> None:
    config.auth_config_source.add_property("pypi-token.foo", "baz")
    manager = PasswordManager(config)

    assert not PoetryKeyring.is_available()
    assert manager.get_pypi_token("foo") == "baz"


def test_delete_pypi_token_with_unavailable_backend(
    config: Config, with_fail_keyring: None
) -> None:
    config.auth_config_source.add_property("pypi-token.foo", "baz")
    manager = PasswordManager(config)

    assert not PoetryKeyring.is_available()
    manager.delete_pypi_token("foo")

    assert config.get("pypi-token.foo") is None


def test_keyring_raises_errors_on_keyring_errors(
    mocker: MockerFixture, with_fail_keyring: None
) -> None:
    mocker.patch("poetry.utils.password_manager.PoetryKeyring.is_available")

    key_ring = PoetryKeyring("poetry")
    with pytest.raises(PoetryKeyringError):
        key_ring.set_password("foo", "bar", "baz")

    with pytest.raises(PoetryKeyringError):
        key_ring.get_password("foo", "bar")

    with pytest.raises(PoetryKeyringError):
        key_ring.delete_password("foo", "bar")


def test_keyring_returns_none_on_locked_keyring(
    with_locked_keyring: None,
    caplog: LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger="poetry.utils.password_manager")
    key_ring = PoetryKeyring("poetry")

    cred = key_ring.get_credential("foo")

    assert cred.password is None
    assert "Keyring foo is locked" in caplog.messages


def test_keyring_returns_none_on_erroneous_keyring(
    with_erroneous_keyring: None,
    caplog: LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger="poetry.utils.password_manager")
    key_ring = PoetryKeyring("poetry")

    cred = key_ring.get_credential("foo")

    assert cred.password is None
    assert "Accessing keyring foo failed" in caplog.messages


def test_keyring_with_chainer_backend_and_fail_keyring_should_be_unavailable(
    with_chained_fail_keyring: None,
) -> None:
    key_ring = PoetryKeyring("poetry")

    assert not key_ring.is_available()


def test_keyring_with_chainer_backend_and_null_keyring_should_be_unavailable(
    with_chained_null_keyring: None,
) -> None:
    key_ring = PoetryKeyring("poetry")

    assert not key_ring.is_available()


def test_null_keyring_should_be_unavailable(
    with_null_keyring: None,
) -> None:
    key_ring = PoetryKeyring("poetry")

    assert not key_ring.is_available()


def test_fail_keyring_should_be_unavailable(
    with_fail_keyring: None,
) -> None:
    key_ring = PoetryKeyring("poetry")

    assert not key_ring.is_available()


def test_locked_keyring_should_be_available(with_locked_keyring: None) -> None:
    key_ring = PoetryKeyring("poetry")

    assert key_ring.is_available()


def test_erroneous_keyring_should_be_available(with_erroneous_keyring: None) -> None:
    key_ring = PoetryKeyring("poetry")

    assert key_ring.is_available()


def test_get_http_auth_from_environment_variables(
    environ: None, config: Config
) -> None:
    os.environ["POETRY_HTTP_BASIC_FOO_USERNAME"] = "bar"
    os.environ["POETRY_HTTP_BASIC_FOO_PASSWORD"] = "baz"

    manager = PasswordManager(config)

    auth = manager.get_http_auth("foo")
    assert auth == {"username": "bar", "password": "baz"}


def test_get_http_auth_does_not_call_keyring_when_credentials_in_environment_variables(
    environ: None, config: Config
) -> None:
    os.environ["POETRY_HTTP_BASIC_FOO_USERNAME"] = "bar"
    os.environ["POETRY_HTTP_BASIC_FOO_PASSWORD"] = "baz"

    manager = PasswordManager(config)
    manager.keyring = MagicMock()

    auth = manager.get_http_auth("foo")
    assert auth == {"username": "bar", "password": "baz"}
    manager.keyring.get_password.assert_not_called()


def test_get_http_auth_does_not_call_keyring_when_password_in_environment_variables(
    environ: None, config: Config
) -> None:
    config.merge(
        {
            "http-basic": {"foo": {"username": "bar"}},
        }
    )
    os.environ["POETRY_HTTP_BASIC_FOO_PASSWORD"] = "baz"

    manager = PasswordManager(config)
    manager.keyring = MagicMock()

    auth = manager.get_http_auth("foo")
    assert auth == {"username": "bar", "password": "baz"}
    manager.keyring.get_password.assert_not_called()


def test_get_pypi_token_with_env_var_positive(
    mocker: MockerFixture,
    config: Config,
    with_simple_keyring: None,
    dummy_keyring: DummyBackend,
) -> None:
    sample_token = "sampletoken-1234"
    repo_name = "foo"
    manager = PasswordManager(config)
    mocker.patch.dict(
        os.environ,
        {f"POETRY_PYPI_TOKEN_{repo_name.upper()}": sample_token},
    )

    assert manager.get_pypi_token(repo_name) == sample_token


def test_get_pypi_token_with_env_var_not_available(
    config: Config, with_simple_keyring: None, dummy_keyring: DummyBackend
) -> None:
    repo_name = "foo"
    manager = PasswordManager(config)

    result_token = manager.get_pypi_token(repo_name)

    assert result_token is None


def test_disabled_keyring_never_called(
    config: Config, with_simple_keyring: None, dummy_keyring: DummyBackend
) -> None:
    config.config["keyring"]["enabled"] = False
    config.config["http-basic"] = {"onlyuser": {"username": "user"}}

    manager = PasswordManager(config)
    num_public_functions = len([f for f in dir(manager) if not f.startswith("_")])
    if num_public_functions != 10:
        pytest.fail(
            f"A function was added to or removed from the {PasswordManager.__name__} "
            "class without reflecting this change in this test."
        )

    with pytest.raises(PoetryKeyringError) as e:
        _ = manager.keyring

    assert str(e.value) == "Access to keyring was requested, but it is not available"

    # We made sure that accessing a disabled keyring raises an exception.
    # Now we call the PasswordManager functions that do access the keyring to
    # make sure that they never do so when the keyring is disabled.
    manager.set_pypi_token(repo_name="exists", token="token")
    manager.get_pypi_token(repo_name="exists")
    manager.get_pypi_token(repo_name="doesn't exist")
    manager.delete_pypi_token(repo_name="exists")
    manager.delete_pypi_token(repo_name="doesn't exist")
    manager.set_http_password(repo_name="exists", username="user", password="password")
    manager.get_http_auth(repo_name="exists")
    manager.get_http_auth(repo_name="doesn't exist")
    manager.get_http_auth(repo_name="onlyuser")
    manager.delete_http_password(repo_name="exits")
    manager.delete_http_password(repo_name="doesn't exist")
    manager.delete_http_password(repo_name="onlyuser")
    manager.get_credential("a", "b", "c", username="user")
