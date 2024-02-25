from __future__ import annotations

import dataclasses
import functools
import logging

from contextlib import suppress
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from keyring.backend import KeyringBackend

    from poetry.config.config import Config

logger = logging.getLogger(__name__)


class PasswordManagerError(Exception):
    pass


class PoetryKeyringError(Exception):
    pass


@dataclasses.dataclass
class HTTPAuthCredential:
    username: str | None = dataclasses.field(default=None)
    password: str | None = dataclasses.field(default=None)


class PoetryKeyring:
    def __init__(self, namespace: str) -> None:
        self._namespace = namespace

    def get_credential(
        self, *names: str, username: str | None = None
    ) -> HTTPAuthCredential:
        import keyring

        from keyring.errors import KeyringError
        from keyring.errors import KeyringLocked

        for name in names:
            credential = None
            try:
                credential = keyring.get_credential(name, username)
            except KeyringLocked:
                logger.debug("Keyring %s is locked", name)
            except (KeyringError, RuntimeError):
                logger.debug("Accessing keyring %s failed", name, exc_info=True)

            if credential:
                return HTTPAuthCredential(
                    username=credential.username, password=credential.password
                )

        return HTTPAuthCredential(username=username, password=None)

    def get_password(self, name: str, username: str) -> str | None:
        import keyring
        import keyring.errors

        name = self.get_entry_name(name)

        try:
            return keyring.get_password(name, username)
        except (RuntimeError, keyring.errors.KeyringError):
            raise PoetryKeyringError(
                f"Unable to retrieve the password for {name} from the key ring"
            )

    def set_password(self, name: str, username: str, password: str) -> None:
        import keyring
        import keyring.errors

        name = self.get_entry_name(name)

        try:
            keyring.set_password(name, username, password)
        except (RuntimeError, keyring.errors.KeyringError) as e:
            raise PoetryKeyringError(
                f"Unable to store the password for {name} in the key ring: {e}"
            )

    def delete_password(self, name: str, username: str) -> None:
        import keyring.errors

        name = self.get_entry_name(name)

        try:
            keyring.delete_password(name, username)
        except (RuntimeError, keyring.errors.KeyringError):
            raise PoetryKeyringError(
                f"Unable to delete the password for {name} from the key ring"
            )

    def get_entry_name(self, name: str) -> str:
        return f"{self._namespace}-{name}"

    @classmethod
    def is_available(cls) -> bool:
        logger.debug("Checking if keyring is available")
        try:
            import keyring
            import keyring.backend
        except ImportError as e:
            logger.debug("An error occurred while importing keyring: %s", e)
            return False

        def backend_name(backend: KeyringBackend) -> str:
            name: str = backend.name
            return name.split(" ")[0]

        def backend_is_valid(backend: KeyringBackend) -> bool:
            name = backend_name(backend)
            if name in ("chainer", "fail", "null"):
                logger.debug(f"Backend {backend.name!r} is not suitable")
                return False
            elif "plaintext" in backend.name.lower():
                logger.debug(f"Not using plaintext keyring backend {backend.name!r}")
                return False

            return True

        backend = keyring.get_keyring()
        if backend_name(backend) == "chainer":
            backends = keyring.backend.get_all_keyring()
            valid_backend = next((b for b in backends if backend_is_valid(b)), None)
        else:
            valid_backend = backend if backend_is_valid(backend) else None

        if valid_backend is None:
            logger.debug("No valid keyring backend was found")
            return False
        else:
            logger.debug(f"Using keyring backend {backend.name!r}")
            return True


class PasswordManager:
    def __init__(self, config: Config) -> None:
        self._config = config

    @functools.cached_property
    def use_keyring(self) -> bool:
        return self._config.get("keyring.enabled") and PoetryKeyring.is_available()

    @functools.cached_property
    def keyring(self) -> PoetryKeyring:
        if not self.use_keyring:
            raise PoetryKeyringError(
                "Access to keyring was requested, but it is not available"
            )

        return PoetryKeyring("poetry-repository")

    @staticmethod
    def warn_plaintext_credentials_stored() -> None:
        logger.warning("Using a plaintext file to store credentials")

    def set_pypi_token(self, repo_name: str, token: str) -> None:
        if not self.use_keyring:
            self.warn_plaintext_credentials_stored()
            self._config.auth_config_source.add_property(
                f"pypi-token.{repo_name}", token
            )
        else:
            self.keyring.set_password(repo_name, "__token__", token)

    def get_pypi_token(self, repo_name: str) -> str | None:
        """Get PyPi token.

        First checks the environment variables for a token,
        then the configured username/password and the
        available keyring.

        :param repo_name:  Name of repository.
        :return: Returns a token as a string if found, otherwise None.
        """
        token: str | None = self._config.get(f"pypi-token.{repo_name}")
        if token:
            return token

        if self.use_keyring:
            return self.keyring.get_password(repo_name, "__token__")
        else:
            return None

    def delete_pypi_token(self, repo_name: str) -> None:
        if not self.use_keyring:
            return self._config.auth_config_source.remove_property(
                f"pypi-token.{repo_name}"
            )

        self.keyring.delete_password(repo_name, "__token__")

    def get_http_auth(self, repo_name: str) -> dict[str, str | None] | None:
        username = self._config.get(f"http-basic.{repo_name}.username")
        password = self._config.get(f"http-basic.{repo_name}.password")
        if not username and not password:
            return None

        if not password:
            if self.use_keyring:
                password = self.keyring.get_password(repo_name, username)
            else:
                return None

        return {
            "username": username,
            "password": password,
        }

    def set_http_password(self, repo_name: str, username: str, password: str) -> None:
        auth = {"username": username}

        if not self.use_keyring:
            self.warn_plaintext_credentials_stored()
            auth["password"] = password
        else:
            self.keyring.set_password(repo_name, username, password)

        self._config.auth_config_source.add_property(f"http-basic.{repo_name}", auth)

    def delete_http_password(self, repo_name: str) -> None:
        auth = self.get_http_auth(repo_name)
        if not auth:
            return

        username = auth.get("username")
        if username is None:
            return

        with suppress(PoetryKeyringError):
            self.keyring.delete_password(repo_name, username)

        self._config.auth_config_source.remove_property(f"http-basic.{repo_name}")

    def get_credential(
        self, *names: str, username: str | None = None
    ) -> HTTPAuthCredential:
        if self.use_keyring:
            return self.keyring.get_credential(*names, username=username)
        else:
            return HTTPAuthCredential(username=username, password=None)
