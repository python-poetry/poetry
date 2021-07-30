import logging
import time

from typing import TYPE_CHECKING

import requests
import requests.auth
import requests.exceptions

from poetry.exceptions import PoetryException
from poetry.utils._compat import urlparse
from poetry.utils.password_manager import PasswordManager


if TYPE_CHECKING:
    from typing import Any
    from typing import Dict
    from typing import Optional
    from typing import Tuple

    from clikit.api.io import IO

    from poetry.config.config import Config


logger = logging.getLogger()


class Authenticator(object):
    def __init__(self, config, io=None):  # type: (Config, Optional[IO]) -> None
        self._config = config
        self._io = io
        self._credentials = {}
        self._password_manager = PasswordManager(self._config)

    def _log(self, message, level="debug"):  # type: (str, str) -> None
        if self._io is not None:
            self._io.write_line(
                "<{level:s}>{message:s}</{level:s}>".format(
                    message=message, level=level
                )
            )
        else:
            getattr(logger, level, logger.debug)(message)

    @property
    def session(self):  # type: () -> requests.Session
        return requests.Session()

    def request(
        self, method, url, **kwargs
    ):  # type: (str, str, Any) -> requests.Response
        request = requests.Request(method, url)
        username, password = self.get_credentials_for_url(url)

        if username is not None and password is not None:
            request = requests.auth.HTTPBasicAuth(username, password)(request)

        session = self.session
        prepared_request = session.prepare_request(request)

        proxies = kwargs.get("proxies", {})
        stream = kwargs.get("stream")
        verify = kwargs.get("verify")
        cert = kwargs.get("cert")

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
                self._log(
                    "Retrying HTTP request in {} seconds.".format(delay), level="debug"
                )
                time.sleep(delay)
                continue

        # this should never really be hit under any sane circumstance
        raise PoetryException("Failed HTTP {} request", method.upper())

    def get_credentials_for_url(
        self, url
    ):  # type: (str) -> Tuple[Optional[str], Optional[str]]
        parsed_url = urlparse.urlsplit(url)

        netloc = parsed_url.netloc

        credentials = self._credentials.get(netloc, (None, None))

        if credentials == (None, None):
            if "@" not in netloc:
                credentials = self._get_credentials_for_netloc(netloc)
            else:
                # Split from the right because that's how urllib.parse.urlsplit()
                # behaves if more than one @ is present (which can be checked using
                # the password attribute of urlsplit()'s return value).
                auth, netloc = netloc.rsplit("@", 1)
                if ":" in auth:
                    # Split from the left because that's how urllib.parse.urlsplit()
                    # behaves if more than one : is present (which again can be checked
                    # using the password attribute of the return value)
                    credentials = auth.split(":", 1)
                else:
                    credentials = auth, None

                credentials = tuple(
                    None if x is None else urlparse.unquote(x) for x in credentials
                )

        if credentials[0] is not None or credentials[1] is not None:
            credentials = (credentials[0] or "", credentials[1] or "")

            self._credentials[netloc] = credentials

        return credentials[0], credentials[1]

    def get_pypi_token(self, name):
        return self._password_manager.get_pypi_token(name)

    def get_http_auth(self, name):  # type: (str) -> Optional[Dict[str, str]]
        return self._get_http_auth(name, None)

    def _get_http_auth(
        self, name, netloc
    ):  # type: (str, Optional[str]) -> Optional[Dict[str, str]]
        if name == "pypi":
            url = "https://upload.pypi.org/legacy/"
        else:
            url = self._config.get("repositories.{}.url".format(name))
            if not url:
                return

        parsed_url = urlparse.urlsplit(url)

        if netloc is None or netloc == parsed_url.netloc:
            auth = self._password_manager.get_http_auth(name)

            if auth is None or auth["password"] is None:
                username = auth["username"] if auth else None
                auth = self._get_credentials_for_netloc_from_keyring(
                    url, parsed_url.netloc, username
                )

            return auth

    def _get_credentials_for_netloc(
        self, netloc
    ):  # type: (str) -> Tuple[Optional[str], Optional[str]]
        credentials = (None, None)

        for repository_name in self._config.get("repositories", []):
            auth = self._get_http_auth(repository_name, netloc)

            if auth is None:
                continue

            return auth["username"], auth["password"]

        return credentials

    def _get_credentials_for_netloc_from_keyring(
        self, url, netloc, username
    ):  # type: (str, str, Optional[str]) -> Optional[Dict[str, str]]
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
