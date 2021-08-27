import re
import uuid

<<<<<<< HEAD
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import List
from typing import Type
from typing import Union

=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
import httpretty
import pytest
import requests

from cleo.io.null_io import NullIO
<<<<<<< HEAD
from dataclasses import dataclass
=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

from poetry.utils.authenticator import Authenticator


<<<<<<< HEAD
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
=======
class SimpleCredential:
    def __init__(self, username, password):
        self.username = username
        self.password = password


@pytest.fixture()
def mock_remote(http):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    http.register_uri(
        http.GET,
        re.compile("^https?://foo.bar/(.+?)$"),
    )


<<<<<<< HEAD
def test_authenticator_uses_url_provided_credentials(
    config: "Config", mock_remote: None, http: Type[httpretty.httpretty]
):
=======
def test_authenticator_uses_url_provided_credentials(config, mock_remote, http):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo001:bar002@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

<<<<<<< HEAD
    assert request.headers["Authorization"] == "Basic Zm9vMDAxOmJhcjAwMg=="


def test_authenticator_uses_credentials_from_config_if_not_provided(
    config: "Config", mock_remote: None, http: Type[httpretty.httpretty]
=======
    assert "Basic Zm9vMDAxOmJhcjAwMg==" == request.headers["Authorization"]


def test_authenticator_uses_credentials_from_config_if_not_provided(
    config, mock_remote, http
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

<<<<<<< HEAD
    assert request.headers["Authorization"] == "Basic YmFyOmJheg=="


def test_authenticator_uses_username_only_credentials(
    config: "Config",
    mock_remote: None,
    http: Type[httpretty.httpretty],
    with_simple_keyring: None,
=======
    assert "Basic YmFyOmJheg==" == request.headers["Authorization"]


def test_authenticator_uses_username_only_credentials(
    config, mock_remote, http, with_simple_keyring
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

<<<<<<< HEAD
    assert request.headers["Authorization"] == "Basic Zm9vMDAxOg=="


def test_authenticator_uses_password_only_credentials(
    config: "Config", mock_remote: None, http: Type[httpretty.httpretty]
):
=======
    assert "Basic Zm9vMDAxOg==" == request.headers["Authorization"]


def test_authenticator_uses_password_only_credentials(config, mock_remote, http):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar/simple/"}},
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://:bar002@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

<<<<<<< HEAD
    assert request.headers["Authorization"] == "Basic OmJhcjAwMg=="


def test_authenticator_uses_empty_strings_as_default_password(
    config: "Config",
    mock_remote: None,
    http: Type[httpretty.httpretty],
    with_simple_keyring: None,
=======
    assert "Basic OmJhcjAwMg==" == request.headers["Authorization"]


def test_authenticator_uses_empty_strings_as_default_password(
    config, mock_remote, http, with_simple_keyring
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

<<<<<<< HEAD
    assert request.headers["Authorization"] == "Basic YmFyOg=="


def test_authenticator_uses_empty_strings_as_default_username(
    config: "Config", mock_remote: None, http: Type[httpretty.httpretty]
=======
    assert "Basic YmFyOg==" == request.headers["Authorization"]


def test_authenticator_uses_empty_strings_as_default_username(
    config, mock_remote, http
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

<<<<<<< HEAD
    assert request.headers["Authorization"] == "Basic OmJhcg=="


def test_authenticator_falls_back_to_keyring_url(
    config: "Config",
    mock_remote: None,
    http: Type[httpretty.httpretty],
    with_simple_keyring: None,
    dummy_keyring: "DummyBackend",
=======
    assert "Basic OmJhcg==" == request.headers["Authorization"]


def test_authenticator_falls_back_to_keyring_url(
    config, mock_remote, http, with_simple_keyring, dummy_keyring
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

<<<<<<< HEAD
    assert request.headers["Authorization"] == "Basic OmJhcg=="


def test_authenticator_falls_back_to_keyring_netloc(
    config: "Config",
    mock_remote: None,
    http: Type[httpretty.httpretty],
    with_simple_keyring: None,
    dummy_keyring: "DummyBackend",
=======
    assert "Basic OmJhcg==" == request.headers["Authorization"]


def test_authenticator_falls_back_to_keyring_netloc(
    config, mock_remote, http, with_simple_keyring, dummy_keyring
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

<<<<<<< HEAD
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
=======
    assert "Basic OmJhcg==" == request.headers["Authorization"]


def test_authenticator_request_retries_on_exception(mocker, config, http):
    sleep = mocker.patch("time.sleep")
    sdist_uri = "https://foo.bar/files/{}/foo-0.1.0.tar.gz".format(str(uuid.uuid4()))
    content = str(uuid.uuid4())
    seen = list()

    def callback(request, uri, response_headers):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        if seen.count(uri) < 2:
            seen.append(uri)
            raise requests.exceptions.ConnectionError("Disconnected")
        return [200, response_headers, content]

    httpretty.register_uri(httpretty.GET, sdist_uri, body=callback)

    authenticator = Authenticator(config, NullIO())
    response = authenticator.request("get", sdist_uri)
    assert response.text == content
    assert sleep.call_count == 2


<<<<<<< HEAD
@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_authenticator_request_raises_exception_when_attempts_exhausted(
    mocker: "MockerFixture", config: "Config", http: Type[httpretty.httpretty]
):
    sleep = mocker.patch("time.sleep")
    sdist_uri = f"https://foo.bar/files/{uuid.uuid4()!s}/foo-0.1.0.tar.gz"

    def callback(*_: Any, **___: Any) -> None:
=======
def test_authenticator_request_raises_exception_when_attempts_exhausted(
    mocker, config, http
):
    sleep = mocker.patch("time.sleep")
    sdist_uri = "https://foo.bar/files/{}/foo-0.1.0.tar.gz".format(str(uuid.uuid4()))

    def callback(*_, **__):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        raise requests.exceptions.ConnectionError(str(uuid.uuid4()))

    httpretty.register_uri(httpretty.GET, sdist_uri, body=callback)
    authenticator = Authenticator(config, NullIO())

    with pytest.raises(requests.exceptions.ConnectionError):
        authenticator.request("get", sdist_uri)

    assert sleep.call_count == 5


@pytest.mark.parametrize(
<<<<<<< HEAD
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
=======
    "status, attempts",
    [(400, 0), (401, 0), (403, 0), (404, 0), (500, 0), (502, 5), (503, 5), (504, 5)],
)
def test_authenticator_request_retries_on_status_code(
    mocker, config, http, status, attempts
):
    sleep = mocker.patch("time.sleep")
    sdist_uri = "https://foo.bar/files/{}/foo-0.1.0.tar.gz".format(str(uuid.uuid4()))
    content = str(uuid.uuid4())

    def callback(request, uri, response_headers):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        return [status, response_headers, content]

    httpretty.register_uri(httpretty.GET, sdist_uri, body=callback)
    authenticator = Authenticator(config, NullIO())

    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        authenticator.request("get", sdist_uri)

    assert excinfo.value.response.status_code == status
    assert excinfo.value.response.text == content

    assert sleep.call_count == attempts


@pytest.fixture
<<<<<<< HEAD
def environment_repository_credentials(monkeypatch: "MonkeyPatch") -> None:
=======
def environment_repository_credentials(monkeypatch):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    monkeypatch.setenv("POETRY_HTTP_BASIC_FOO_USERNAME", "bar")
    monkeypatch.setenv("POETRY_HTTP_BASIC_FOO_PASSWORD", "baz")


def test_authenticator_uses_env_provided_credentials(
<<<<<<< HEAD
    config: "Config",
    environ: None,
    mock_remote: Type[httpretty.httpretty],
    http: Type[httpretty.httpretty],
    environment_repository_credentials: None,
=======
    config, environ, mock_remote, http, environment_repository_credentials
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    config.merge({"repositories": {"foo": {"url": "https://foo.bar/simple/"}}})

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

<<<<<<< HEAD
    assert request.headers["Authorization"] == "Basic YmFyOmJheg=="
=======
    assert "Basic YmFyOmJheg==" == request.headers["Authorization"]
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
