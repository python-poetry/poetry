import base64

from requests import Request

from poetry.repositories.auth import Auth
from poetry.utils._compat import decode
from poetry.utils._compat import encode


def test_auth_with_request_on_the_same_host():
    auth = Auth("https://python-poetry.org", "foo", "bar")

    request = Request("GET", "https://python-poetry.org/docs/")
    assert "Authorization" not in request.headers

    request = auth(request)

    assert "Authorization" in request.headers
    assert request.headers["Authorization"] == "Basic {}".format(
        decode(base64.b64encode(encode(":".join(("foo", "bar")))))
    )


def test_auth_with_request_with_same_authentication():
    auth = Auth("https://python-poetry.org", "foo", "bar")

    request = Request("GET", "https://foo:bar@python-poetry.org/docs/")
    assert "Authorization" not in request.headers

    request = auth(request)

    assert "Authorization" in request.headers
    assert request.headers["Authorization"] == "Basic {}".format(
        decode(base64.b64encode(encode(":".join(("foo", "bar")))))
    )


def test_auth_with_request_on_different_hosts():
    auth = Auth("https://python-poetry.org", "foo", "bar")

    request = Request("GET", "https://pendulum.eustace.io/docs/")
    assert "Authorization" not in request.headers

    request = auth(request)

    assert "Authorization" not in request.headers
