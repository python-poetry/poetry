from typing import TYPE_CHECKING

from poetry.utils._compat import urlparse
from poetry.utils.password_manager import PasswordManager


if TYPE_CHECKING:
    from typing import Any
    from typing import Optional
    from typing import Tuple

    from clikit.api.io import IO
    from requests import Request  # noqa
    from requests import Response  # noqa
    from requests import Session  # noqa

    from poetry.config.config import Config


class Authenticator(object):
    def __init__(self, config, io):  # type: (Config, IO) -> None
        self._config = config
        self._io = io
        self._session = None
        self._credentials = {}
        self._password_manager = PasswordManager(self._config)

    @property
    def session(self):  # type: () -> Session
        from requests import Session  # noqa

        if self._session is None:
            self._session = Session()

        return self._session

    def request(self, method, url, **kwargs):  # type: (str, str, Any) -> Response
        from requests import Request  # noqa
        from requests.auth import HTTPBasicAuth

        request = Request(method, url)

        username, password = self._get_credentials_for_url(url)

        if username is not None and password is not None:
            request = HTTPBasicAuth(username, password)(request)

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
        resp = session.send(prepared_request, **send_kwargs)

        resp.raise_for_status()

        return resp

    def _get_credentials_for_url(
        self, url
    ):  # type: (str) -> Tuple[Optional[str], Optional[str]]
        parsed_url = urlparse.urlsplit(url)

        netloc = parsed_url.netloc

        credentials = self._credentials.get(netloc, (None, None))

        if credentials == (None, None):
            if "@" not in netloc:
                credentials = self._get_credentials_for_netloc_from_config(netloc)
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

    def _get_credentials_for_netloc_from_config(
        self, netloc
    ):  # type: (str) -> Tuple[Optional[str], Optional[str]]
        credentials = (None, None)
        for repository_name in self._config.get("http-basic", {}):
            repository_config = self._config.get(
                "repositories.{}".format(repository_name)
            )
            if not repository_config:
                continue

            url = repository_config.get("url")
            if not url:
                continue

            parsed_url = urlparse.urlsplit(url)

            if netloc == parsed_url.netloc:
                auth = self._password_manager.get_http_auth(repository_name)

                if auth is None:
                    continue

                return auth["username"], auth["password"]

        return credentials
