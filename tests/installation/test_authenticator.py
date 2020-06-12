import re

import pytest

from poetry.installation.authenticator import Authenticator
from poetry.io.null_io import NullIO


@pytest.fixture()
def mock_remote(http):
    http.register_uri(
        http.GET, re.compile("^https?://foo.bar/(.+?)$"),
    )


def test_authenticator_uses_url_provided_credentials(config, mock_remote, http):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo001:bar002@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert "Basic Zm9vMDAxOmJhcjAwMg==" == request.headers["Authorization"]


def test_authenticator_uses_credentials_from_config_if_not_provided(
    config, mock_remote, http
):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert "Basic YmFyOmJheg==" == request.headers["Authorization"]


def test_authenticator_uses_username_only_credentials(config, mock_remote, http):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo001@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert "Basic Zm9vMDAxOg==" == request.headers["Authorization"]


def test_authenticator_uses_password_only_credentials(config, mock_remote, http):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://:bar002@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert "Basic OmJhcjAwMg==" == request.headers["Authorization"]


def test_authenticator_uses_empty_strings_as_default_password(
    config, mock_remote, http
):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert "Basic YmFyOg==" == request.headers["Authorization"]


def test_authenticator_uses_empty_strings_as_default_username(
    config, mock_remote, http
):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": None, "password": "bar"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert "Basic OmJhcg==" == request.headers["Authorization"]
