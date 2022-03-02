from __future__ import annotations

import logging

from contextlib import suppress
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from poetry.config.config import Config

logger = logging.getLogger(__name__)


class PasswordManagerError(Exception):

    pass


class KeyRingError(Exception):

    pass


class KeyRing:
    def __init__(self, namespace: str) -> None:
        self._namespace = namespace
        self._is_available = True

        self._check()

    def is_available(self) -> bool:
        return self._is_available

    def get_password(self, name: str, username: str) -> str | None:
        if not self.is_available():
            return None

        import keyring
        import keyring.errors

        name = self.get_entry_name(name)

        try:
            return keyring.get_password(name, username)
        except (RuntimeError, keyring.errors.KeyringError):
            raise KeyRingError(
                f"Unable to retrieve the password for {name} from the key ring"
            )

    def set_password(self, name: str, username: str, password: str) -> None:
        if not self.is_available():
            return

        import keyring
        import keyring.errors

        name = self.get_entry_name(name)

        try:
            keyring.set_password(name, username, password)
        except (RuntimeError, keyring.errors.KeyringError) as e:
            raise KeyRingError(
                f"Unable to store the password for {name} in the key ring: {e}"
            )

    def delete_password(self, name: str, username: str) -> None:
        if not self.is_available():
            return

        import keyring
        import keyring.errors

        name = self.get_entry_name(name)

        try:
            keyring.delete_password(name, username)
        except (RuntimeError, keyring.errors.KeyringError):
            raise KeyRingError(
                f"Unable to delete the password for {name} from the key ring"
            )

    def get_entry_name(self, name: str) -> str:
        return f"{self._namespace}-{name}"

    def _check(self) -> None:
        try:
            import keyring
        except Exception as e:
            logger.debug(f"An error occurred while importing keyring: {e!s}")
            self._is_available = False

            return

        backend = keyring.get_keyring()
        name = backend.name.split(" ")[0]
        if name == "fail":
            logger.debug("No suitable keyring backend found")
            self._is_available = False
        elif "plaintext" in backend.name.lower():
            logger.debug("Only a plaintext keyring backend is available. Not using it.")
            self._is_available = False
        elif name == "chainer":
            try:
                import keyring.backend

                backends = keyring.backend.get_all_keyring()

                self._is_available = any(
                    b.name.split(" ")[0] not in ["chainer", "fail"]
                    and "plaintext" not in b.name.lower()
                    for b in backends
                )
            except Exception:
                self._is_available = False

        if not self._is_available:
            logger.warning("No suitable keyring backends were found")


class PasswordManager:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._keyring: KeyRing | None = None

    @property
    def keyring(self) -> KeyRing:
        if self._keyring is None:
            self._keyring = KeyRing("poetry-repository")
            if not self._keyring.is_available():
                logger.warning(
                    "Using a plaintext file to store and retrieve credentials"
                )

        return self._keyring

    def set_pypi_token(self, name: str, token: str) -> None:
        if not self.keyring.is_available():
            self._config.auth_config_source.add_property(f"pypi-token.{name}", token)
        else:
            self.keyring.set_password(name, "__token__", token)

    def get_pypi_token(self, name: str) -> str:
        token = self.keyring.get_password(name, "__token__")
        if token is not None:
            return token
        return self._config.get(f"pypi-token.{name}")

    def delete_pypi_token(self, name: str) -> None:
        if not self.keyring.is_available():
            self._config.auth_config_source.remove_property(f"pypi-token.{name}")
            return

        self.keyring.delete_password(name, "__token__")

    def get_http_auth(self, name: str) -> dict[str, str] | None:
        auth = self._config.get(f"http-basic.{name}")
        if not auth:
            username = self._config.get(f"http-basic.{name}.username")
            password = self._config.get(f"http-basic.{name}.password")
            if not username and not password:
                return None
        else:
            username, password = auth["username"], auth.get("password")
            if password is None:
                password = self.keyring.get_password(name, username)

        return {
            "username": username,
            "password": password,
        }

    def set_http_password(self, name: str, username: str, password: str) -> None:
        auth = {"username": username}

        if not self.keyring.is_available():
            auth["password"] = password
        else:
            self.keyring.set_password(name, username, password)

        self._config.auth_config_source.add_property(f"http-basic.{name}", auth)

    def delete_http_password(self, name: str) -> None:
        auth = self.get_http_auth(name)
        if not auth or "username" not in auth:
            return

        with suppress(KeyRingError):
            self.keyring.delete_password(name, auth["username"])

        self._config.auth_config_source.remove_property(f"http-basic.{name}")
