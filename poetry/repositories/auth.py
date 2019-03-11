from requests import Request
from requests.auth import AuthBase
from requests.auth import HTTPBasicAuth

from poetry.utils._compat import urlparse


def _hostnames_matches(url, base_url):
    return urlparse.urlparse(url).hostname == urlparse.urlparse(base_url).hostname


class Auth(AuthBase):
    def __init__(self, url, username, password):  # type: (str, str, str) -> None
        self._url = url
        self._username = username
        self._password = password

    def __call__(self, r):  # type: (Request) -> Request
        if not _hostnames_matches(r.url, self._url):
            return r

        HTTPBasicAuth(self._username, self._password)(r)

        return r


class URLAuth(AuthBase):
    def __init__(self, url, username, password):  # type: (str, str, str) -> None

        self._url = url
        self._username = username
        self._password = password

    def __call__(self, r):  # type: (Request) -> Request
        if not _hostnames_matches(r.url, self._url):
            return r

        url_parts = urlparse.urlparse(r.url)
        netrc_url = "{}:{}@{}".format(
            urlparse.quote(self._username, safe=""),
            urlparse.quote(self._password, safe=""),
            url_parts[1],
        )
        r.url = urlparse.urlunparse([url_parts[0], netrc_url, *url_parts[2:]])
        return r

    @classmethod
    def from_auth(cls, auth):  # type: (Auth) -> URLAuth
        return URLAuth(auth._url, auth._username, auth._password)
