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
        self._session = None
        self._credentials = {}
        self._certs = {}
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

        credentials = self._credentials.get(url, (None, None))

        if credentials == (None, None):
            if "@" not in parsed_url.netloc:
                credentials = self._get_credentials_for_url(url)
            else:
                # Split from the right because that's how urllib.parse.urlsplit()
                # behaves if more than one @ is present (which can be checked using
                # the password attribute of urlsplit()'s return value).
                auth, netloc = parsed_url.netloc.rsplit("@", 1)
                # Split from the left because that's how urllib.parse.urlsplit()
                # behaves if more than one : is present (which again can be checked
                # using the password attribute of the return value)
                credentials = auth.split(":", 1) if ":" in auth else (auth, None)
                credentials = tuple(
                    None if x is None else urllib.parse.unquote(x) for x in credentials
                )

        if credentials[0] is not None or credentials[1] is not None:
            credentials = (credentials[0] or "", credentials[1] or "")

            self._credentials[url] = credentials

        return credentials[0], credentials[1]

    def get_pypi_token(self, name: str) -> str:
        return self._password_manager.get_pypi_token(name)

    def get_http_auth(self, name: str) -> dict[str, str] | None:
        return self._get_http_auth(name, None)

    def _get_http_auth(self, name: str, url: str | None) -> dict[str, str] | None:
        if name == "pypi":
            repository_url = "https://upload.pypi.org/legacy/"
        else:
            repository_url = self._config.get(f"repositories.{name}.url")
            if not repository_url:
                return None

        parsed_repository_url = urllib.parse.urlsplit(repository_url)
        parsed_package_url = urllib.parse.urlsplit(url)

        if url is None or (
            parsed_repository_url.netloc == parsed_package_url.netloc
            and parsed_package_url.path.startswith(parsed_repository_url.path)
        ):
            auth = self._password_manager.get_http_auth(name)

            if auth is None or auth["password"] is None:
                username = auth["username"] if auth else None
                auth = self._get_credentials_for_url_from_keyring(
                    repository_url, username
                )

            return auth

    def _get_credentials_for_url(self, url: str) -> tuple[str | None, str | None]:
        for repository_name, _ in self._get_repository_urls():
            auth = self._get_http_auth(repository_name, url)

            if auth is None:
                continue

            return auth["username"], auth["password"]

        return None, None

    def get_certs_for_url(self, url: str) -> dict[str, Path | None]:
        return self._certs.setdefault(
            url,
            self._get_certs_for_url_from_config(url),
        )

    def _get_repository_urls(self) -> Iterator[tuple[str, str]]:
        for repository_name in self._config.get("repositories", []):
            yield repository_name, self._config.get(
                f"repositories.{repository_name}.url"
            )

    def _get_credentials_for_url_from_keyring(
        self, url: str, username: str | None
    ) -> dict[str, str] | None:
        import keyring

        cred = keyring.get_credential(url, username)
        if cred is not None:
            return {
                "username": cred.username,
                "password": cred.password,
            }

        parsed_url = urllib.parse.urlsplit(url)
        cred = keyring.get_credential(parsed_url.netloc, username)
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

    def _get_certs_for_url_from_config(self, url: str) -> dict[str, Path | None]:
        certs = {"cert": None, "verify": None}

        for repository_name, repository_url in self._get_repository_urls():
            if url == repository_url:
                certs["cert"] = get_client_cert(self._config, repository_name)
                certs["verify"] = get_cert(self._config, repository_name)
                break

        return certs
