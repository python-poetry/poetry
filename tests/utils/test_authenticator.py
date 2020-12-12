import pathlib
import re
import uuid

from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import List
from typing import Type
from typing import Union

import httpretty
import pytest
import requests

from cleo.io.null_io import NullIO
from dataclasses import dataclass

from poetry.utils.authenticator import Authenticator


if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock import MockerFixture

    from tests.conftest import Config
    from tests.conftest import DummyBackend


@dataclass
class SimpleCredential:
    username: str
    password: str


@pytest.fixture()
def mock_remote(http: Type[httpretty.httpretty]) -> None:
    http.register_uri(
        http.GET,
        re.compile("^https?://foo.bar/(.+?)$"),
    )


def test_authenticator_uses_url_provided_credentials(
    config: "Config", mock_remote: None, http: Type[httpretty.httpretty]
):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo001:bar002@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert request.headers["Authorization"] == "Basic Zm9vMDAxOmJhcjAwMg=="


def test_authenticator_uses_credentials_from_config_if_not_provided(
    config: "Config", mock_remote: None, http: Type[httpretty.httpretty]
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

    assert request.headers["Authorization"] == "Basic YmFyOmJheg=="


def test_authenticator_uses_username_only_credentials(
    config: "Config",
    mock_remote: None,
    http: Type[httpretty.httpretty],
    with_simple_keyring: None,
):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo001@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert request.headers["Authorization"] == "Basic Zm9vMDAxOg=="


def test_authenticator_uses_password_only_credentials(
    config: "Config", mock_remote: None, http: Type[httpretty.httpretty]
):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://:bar002@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert request.headers["Authorization"] == "Basic OmJhcjAwMg=="


def test_authenticator_uses_empty_strings_as_default_password(
    config: "Config",
    mock_remote: None,
    http: Type[httpretty.httpretty],
    with_simple_keyring: None,
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

    assert request.headers["Authorization"] == "Basic YmFyOg=="


def test_authenticator_uses_empty_strings_as_default_username(
    config: "Config", mock_remote: None, http: Type[httpretty.httpretty]
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

    assert request.headers["Authorization"] == "Basic OmJhcg=="


def test_authenticator_falls_back_to_keyring_url(
    config: "Config",
    mock_remote: None,
    http: Type[httpretty.httpretty],
    with_simple_keyring: None,
    dummy_keyring: "DummyBackend",
):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
        }
    )

    dummy_keyring.set_password(
        "https://foo.bar/simple/", None, SimpleCredential(None, "bar")
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert request.headers["Authorization"] == "Basic OmJhcg=="


def test_authenticator_falls_back_to_keyring_netloc(
    config: "Config",
    mock_remote: None,
    http: Type[httpretty.httpretty],
    with_simple_keyring: None,
    dummy_keyring: "DummyBackend",
):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
        }
    )

    dummy_keyring.set_password("foo.bar", None, SimpleCredential(None, "bar"))

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert request.headers["Authorization"] == "Basic OmJhcg=="


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_authenticator_request_retries_on_exception(
    mocker: "MockerFixture", config: "Config", http: Type[httpretty.httpretty]
):
    sleep = mocker.patch("time.sleep")
    sdist_uri = f"https://foo.bar/files/{uuid.uuid4()!s}/foo-0.1.0.tar.gz"
    content = str(uuid.uuid4())
    seen = []

    def callback(
        request: requests.Request, uri: str, response_headers: Dict
    ) -> List[Union[int, Dict, str]]:
        if seen.count(uri) < 2:
            seen.append(uri)
            raise requests.exceptions.ConnectionError("Disconnected")
        return [200, response_headers, content]

    httpretty.register_uri(httpretty.GET, sdist_uri, body=callback)

    authenticator = Authenticator(config, NullIO())
    response = authenticator.request("get", sdist_uri)
    assert response.text == content
    assert sleep.call_count == 2


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_authenticator_request_raises_exception_when_attempts_exhausted(
    mocker: "MockerFixture", config: "Config", http: Type[httpretty.httpretty]
):
    sleep = mocker.patch("time.sleep")
    sdist_uri = f"https://foo.bar/files/{uuid.uuid4()!s}/foo-0.1.0.tar.gz"

    def callback(*_: Any, **___: Any) -> None:
        raise requests.exceptions.ConnectionError(str(uuid.uuid4()))

    httpretty.register_uri(httpretty.GET, sdist_uri, body=callback)
    authenticator = Authenticator(config, NullIO())

    with pytest.raises(requests.exceptions.ConnectionError):
        authenticator.request("get", sdist_uri)

    assert sleep.call_count == 5


@pytest.mark.parametrize(
    ["status", "attempts"],
    [
        (400, 0),
        (401, 0),
        (403, 0),
        (404, 0),
        (500, 0),
        (502, 5),
        (503, 5),
        (504, 5),
    ],
)
def test_authenticator_request_retries_on_status_code(
    mocker: "MockerFixture",
    config: "Config",
    http: Type[httpretty.httpretty],
    status: int,
    attempts: int,
):
    sleep = mocker.patch("time.sleep")
    sdist_uri = f"https://foo.bar/files/{uuid.uuid4()!s}/foo-0.1.0.tar.gz"
    content = str(uuid.uuid4())

    def callback(
        request: requests.Request, uri: str, response_headers: Dict
    ) -> List[Union[int, Dict, str]]:
        return [status, response_headers, content]

    httpretty.register_uri(httpretty.GET, sdist_uri, body=callback)
    authenticator = Authenticator(config, NullIO())

    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        authenticator.request("get", sdist_uri)

    assert excinfo.value.response.status_code == status
    assert excinfo.value.response.text == content

    assert sleep.call_count == attempts


@pytest.fixture
def environment_repository_credentials(monkeypatch: "MonkeyPatch") -> None:
    monkeypatch.setenv("POETRY_HTTP_BASIC_FOO_USERNAME", "bar")
    monkeypatch.setenv("POETRY_HTTP_BASIC_FOO_PASSWORD", "baz")


def test_authenticator_uses_env_provided_credentials(
    config: "Config",
    environ: None,
    mock_remote: Type[httpretty.httpretty],
    http: Type[httpretty.httpretty],
    environment_repository_credentials: None,
):
    config.merge({"repositories": {"foo": {"url": "https://foo.bar/simple/"}}})

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    assert request.headers["Authorization"] == "Basic YmFyOmJheg=="


def test_authenticator_uses_certs_from_config_if_not_provided(
    config, mock_remote, http, mocker
):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
            "certificates": {"foo": {
                "cert": "/path/to/cert",
                "client-cert": "/path/to/client-cert",
            }},
        }
    )

    authenticator = Authenticator(config, NullIO())
    session_send = mocker.patch.object(authenticator.session, "send")
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")
    call_args = session_send.call_args
    call_args.kwargs["verify"] == pathlib.Path("/path/to/cert")
    call_args.kwargs["cert"] == pathlib.Path("/path/to/client-cert")


def test_authenticator_uses_provided_certs_instead_of_config_certs(
    config, mock_remote, http, mocker
):
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
            "certificates": {"foo": {
                "cert": "/path/to/cert",
                "client-cert": "/path/to/client-cert",
            }},
        }
    )

    authenticator = Authenticator(config, NullIO())
    session_send = mocker.patch.object(authenticator.session, "send")
    authenticator.request(
        "get",
        "https://foo.bar/files/foo-0.1.0.tar.gz",
        verify="/path/to/provided/cert",
        cert="/path/to/provided/client-cert",
    )
    call_args = session_send.call_args
    call_args.kwargs["verify"] == pathlib.Path("/path/to/provided/cert")
    call_args.kwargs["cert"] == pathlib.Path("/path/to/provided/client-cert")
