from __future__ import annotations

import logging
import time
import urllib.parse

from typing import TYPE_CHECKING
from typing import Any
from typing import Iterator

import requests
import requests.auth
import requests.exceptions

from poetry.exceptions import PoetryException
from poetry.utils.helpers import get_cert
from poetry.utils.helpers import get_client_cert
from poetry.utils.password_manager import PasswordManager


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.io.io import IO

    from poetry.config.config import Config


logger = logging.getLogger()


class Authenticator:
    def __init__(self, config: Config, io: IO | None = None) -> None:
        self._config = config
        self._io = io
        self._session: requests.Session | None = None
        self._credentials: dict[str, tuple[str, str]] = {}
        self._certs: dict[str, dict[str, Path | None]] = {}
        self._password_manager = PasswordManager(self._config)

    def _log(self, message: str, level: str = "debug") -> None:
        if self._io is not None:
            self._io.write_line(f"<{level}>{message}</{level}>")
        else:
            getattr(logger, level, logger.debug)(message)

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()

        return self._session

    def __del__(self) -> None:
        if self._session is not None:
            self._session.close()

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        request = requests.Request(method, url)
        username, password = self.get_credentials_for_url(url)

        if username is not None and password is not None:
            request = requests.auth.HTTPBasicAuth(username, password)(request)

        session = self.session
        prepared_request = session.prepare_request(request)

        proxies = kwargs.get("proxies", {})
        stream = kwargs.get("stream")

        certs = self.get_certs_for_url(url)
        verify = kwargs.get("verify") or certs.get("verify")
        cert = kwargs.get("cert") or certs.get("cert")

        if cert is not None:
            cert = str(cert)

        if verify is not None:
            verify = str(verify)

        settings = session.merge_environment_settings(
            prepared_request.url, proxies, stream, verify, cert
        )

        # Send the request.
        send_kwargs = {
            "timeout": kwargs.get("timeout"),
            "allow_redirects": kwargs.get("allow_redirects", True),
        }
        send_kwargs.update(settings)

        attempt = 0

        while True:
            is_last_attempt = attempt >= 5
            try:
                resp = session.send(prepared_request, **send_kwargs)
            except (requests.exceptions.ConnectionError, OSError) as e:
                if is_last_attempt:
                    raise e
            else:
                if resp.status_code not in [502, 503, 504] or is_last_attempt:
                    resp.raise_for_status()
                    return resp

            if not is_last_attempt:
                attempt += 1
                delay = 0.5 * attempt
                self._log(f"Retrying HTTP request in {delay} seconds.", level="debug")
                time.sleep(delay)
                continue

        # this should never really be hit under any sane circumstance
        raise PoetryException("Failed HTTP {} request", method.upper())

    def get_credentials_for_url(self, url: str) -> tuple[str | None, str | None]:
        parsed_url = urllib.parse.urlsplit(url)

        netloc = parsed_url.netloc

        credentials: tuple[str | None, str | None] = self._credentials.get(
            netloc, (None, None)
        )

        if credentials == (None, None):
            if "@" not in netloc:
                credentials = self._get_credentials_for_netloc(netloc)
            else:
                # Split from the right because that's how urllib.parse.urlsplit()
                # behaves if more than one @ is present (which can be checked using
                # the password attribute of urlsplit()'s return value).
                auth, netloc = netloc.rsplit("@", 1)
                # Split from the left because that's how urllib.parse.urlsplit()
                # behaves if more than one : is present (which again can be checked
                # using the password attribute of the return value)
                user, password = auth.split(":", 1) if ":" in auth else (auth, "")
                credentials = (
                    urllib.parse.unquote(user),
                    urllib.parse.unquote(password),
                )

        if any(credential is not None for credential in credentials):
            credentials = (credentials[0] or "", credentials[1] or "")
            self._credentials[netloc] = credentials

        return credentials

    def get_pypi_token(self, name: str) -> str | None:
        return self._password_manager.get_pypi_token(name)

    def get_http_auth(self, name: str) -> dict[str, str | None] | None:
        return self._get_http_auth(name, None)

    def _get_http_auth(
        self, name: str, netloc: str | None
    ) -> dict[str, str | None] | None:
        if name == "pypi":
            url = "https://upload.pypi.org/legacy/"
        else:
            url = self._config.get(f"repositories.{name}.url")
            if not url:
                return None

        parsed_url = urllib.parse.urlsplit(url)

        if netloc is None or netloc == parsed_url.netloc:
            auth = self._password_manager.get_http_auth(name)
            auth = auth or {}

            if auth.get("password") is None:
                username = auth.get("username")
                auth = self._get_credentials_for_netloc_from_keyring(
                    url, parsed_url.netloc, username
                )

            return auth

        return None

    def _get_credentials_for_netloc(self, netloc: str) -> tuple[str | None, str | None]:
        for repository_name, _ in self._get_repository_netlocs():
            auth = self._get_http_auth(repository_name, netloc)

            if auth is None:
                continue

            return auth.get("username"), auth.get("password")

        return None, None

    def get_certs_for_url(self, url: str) -> dict[str, Path | None]:
        parsed_url = urllib.parse.urlsplit(url)

        netloc = parsed_url.netloc

        return self._certs.setdefault(
            netloc,
            self._get_certs_for_netloc_from_config(netloc),
        )

    def _get_repository_netlocs(self) -> Iterator[tuple[str, str]]:
        for repository_name in self._config.get("repositories", []):
            url = self._config.get(f"repositories.{repository_name}.url")
            parsed_url = urllib.parse.urlsplit(url)
            yield repository_name, parsed_url.netloc

    def _get_credentials_for_netloc_from_keyring(
        self, url: str, netloc: str, username: str | None
    ) -> dict[str, str | None] | None:
        import keyring

        cred = keyring.get_credential(url, username)
        if cred is not None:
            return {
                "username": cred.username,
                "password": cred.password,
            }

        cred = keyring.get_credential(netloc, username)
        if cred is not None:
            return {
                "username": cred.username,
                "password": cred.password,
            }

        if username:
            return {
                "username": username,
                "password": None,
            }

        return None

    def _get_certs_for_netloc_from_config(self, netloc: str) -> dict[str, Path | None]:
        certs: dict[str, Path | None] = {"cert": None, "verify": None}

        for repository_name, repository_netloc in self._get_repository_netlocs():
            if netloc == repository_netloc:
                certs["cert"] = get_client_cert(self._config, repository_name)
                certs["verify"] = get_cert(self._config, repository_name)
                break

        return certs
