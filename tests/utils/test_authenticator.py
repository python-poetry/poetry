from __future__ import annotations

import base64
import logging
import re
import uuid

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import httpretty
import pytest
import requests

from cleo.io.null_io import NullIO

from poetry.utils.authenticator import Authenticator
from poetry.utils.authenticator import RepositoryCertificateConfig


if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock import MockerFixture

    from tests.conftest import Config
    from tests.conftest import DummyBackend


@dataclass
class SimpleCredential:
    username: str
    password: str


@pytest.fixture()
def mock_remote(http: type[httpretty.httpretty]) -> None:
    http.register_uri(
        http.GET,
        re.compile("^https?://foo.bar/(.+?)$"),
    )


@pytest.fixture()
def repo() -> dict[str, dict[str, str]]:
    return {"foo": {"url": "https://foo.bar/simple/"}}


@pytest.fixture
def mock_config(config: Config, repo: dict[str, dict[str, str]]) -> Config:
    config.merge(
        {
            "repositories": repo,
            "http-basic": {"foo": {"username": "bar", "password": "baz"}},
        }
    )

    return config


def test_authenticator_uses_url_provided_credentials(
    mock_config: Config, mock_remote: None, http: type[httpretty.httpretty]
) -> None:
    authenticator = Authenticator(mock_config, NullIO())
    authenticator.request("get", "https://foo001:bar002@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()
    basic_auth = base64.b64encode(b"foo001:bar002").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_uses_credentials_from_config_if_not_provided(
    mock_config: Config, mock_remote: None, http: type[httpretty.httpretty]
) -> None:
    authenticator = Authenticator(mock_config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()
    basic_auth = base64.b64encode(b"bar:baz").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_uses_username_only_credentials(
    mock_config: Config,
    mock_remote: None,
    http: type[httpretty.httpretty],
    with_simple_keyring: None,
) -> None:
    authenticator = Authenticator(mock_config, NullIO())
    authenticator.request("get", "https://foo001@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()
    basic_auth = base64.b64encode(b"foo001:").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_ignores_locked_keyring(
    mock_remote: None,
    http: type[httpretty.httpretty],
    with_locked_keyring: None,
    caplog: LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger="poetry.utils.password_manager")
    authenticator = Authenticator()
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()
    assert request.headers["Authorization"] is None
    assert "Keyring foo.bar is locked" in caplog.messages


def test_authenticator_ignores_failing_keyring(
    mock_remote: None,
    http: type[httpretty.httpretty],
    with_erroneous_keyring: None,
    caplog: LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger="poetry.utils.password_manager")
    authenticator = Authenticator()
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()
    assert request.headers["Authorization"] is None
    assert "Accessing keyring foo.bar failed" in caplog.messages


def test_authenticator_uses_password_only_credentials(
    mock_config: Config, mock_remote: None, http: type[httpretty.httpretty]
) -> None:
    authenticator = Authenticator(mock_config, NullIO())
    authenticator.request("get", "https://:bar002@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()
    basic_auth = base64.b64encode(b":bar002").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_uses_empty_strings_as_default_password(
    config: Config,
    mock_remote: None,
    repo: dict[str, dict[str, str]],
    http: type[httpretty.httpretty],
    with_simple_keyring: None,
) -> None:
    config.merge(
        {
            "repositories": repo,
            "http-basic": {"foo": {"username": "bar"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()
    basic_auth = base64.b64encode(b"bar:").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_uses_empty_strings_as_default_username(
    config: Config,
    mock_remote: None,
    repo: dict[str, dict[str, str]],
    http: type[httpretty.httpretty],
) -> None:
    config.merge(
        {
            "repositories": repo,
            "http-basic": {"foo": {"username": None, "password": "bar"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()
    basic_auth = base64.b64encode(b":bar").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_falls_back_to_keyring_url(
    config: Config,
    mock_remote: None,
    repo: dict[str, dict[str, str]],
    http: type[httpretty.httpretty],
    with_simple_keyring: None,
    dummy_keyring: DummyBackend,
) -> None:
    config.merge(
        {
            "repositories": repo,
        }
    )

    dummy_keyring.set_password(
        "https://foo.bar/simple/", None, SimpleCredential("foo", "bar")
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()
    basic_auth = base64.b64encode(b"foo:bar").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_falls_back_to_keyring_netloc(
    config: Config,
    mock_remote: None,
    repo: dict[str, dict[str, str]],
    http: type[httpretty.httpretty],
    with_simple_keyring: None,
    dummy_keyring: DummyBackend,
) -> None:
    config.merge(
        {
            "repositories": repo,
        }
    )

    dummy_keyring.set_password("foo.bar", None, SimpleCredential("foo", "bar"))

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()
    basic_auth = base64.b64encode(b"foo:bar").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_authenticator_request_retries_on_exception(
    mocker: MockerFixture, config: Config, http: type[httpretty.httpretty]
) -> None:
    sleep = mocker.patch("time.sleep")
    sdist_uri = f"https://foo.bar/files/{uuid.uuid4()!s}/foo-0.1.0.tar.gz"
    content = str(uuid.uuid4())
    seen: list[str] = []

    def callback(
        request: requests.Request, uri: str, response_headers: dict[str, str]
    ) -> list[int | dict[str, str] | str]:
        if seen.count(uri) < 2:
            seen.append(uri)
            raise requests.exceptions.ConnectionError("Disconnected")
        return [200, response_headers, content]

    http.register_uri(httpretty.GET, sdist_uri, body=callback)

    authenticator = Authenticator(config, NullIO())
    response = authenticator.request("get", sdist_uri)
    assert response.text == content
    assert sleep.call_count == 2


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_authenticator_request_raises_exception_when_attempts_exhausted(
    mocker: MockerFixture, config: Config, http: type[httpretty.httpretty]
) -> None:
    sleep = mocker.patch("time.sleep")
    sdist_uri = f"https://foo.bar/files/{uuid.uuid4()!s}/foo-0.1.0.tar.gz"

    def callback(*_: Any, **___: Any) -> None:
        raise requests.exceptions.ConnectionError(str(uuid.uuid4()))

    http.register_uri(httpretty.GET, sdist_uri, body=callback)
    authenticator = Authenticator(config, NullIO())

    with pytest.raises(requests.exceptions.ConnectionError):
        authenticator.request("get", sdist_uri)

    assert sleep.call_count == 5


def test_authenticator_request_respects_retry_header(
    mocker: MockerFixture,
    config: Config,
    http: type[httpretty.httpretty],
) -> None:
    sleep = mocker.patch("time.sleep")
    sdist_uri = f"https://foo.bar/files/{uuid.uuid4()!s}/foo-0.1.0.tar.gz"
    content = str(uuid.uuid4())
    seen: list[str] = []

    def callback(
        request: requests.Request, uri: str, response_headers: dict[str, str]
    ) -> list[int | dict[str, str] | str]:
        if not seen.count(uri):
            seen.append(uri)
            return [429, {"Retry-After": "42"}, "Retry later"]

        return [200, response_headers, content]

    http.register_uri(httpretty.GET, sdist_uri, body=callback)
    authenticator = Authenticator(config, NullIO())

    response = authenticator.request("get", sdist_uri)
    assert sleep.call_args[0] == (42.0,)
    assert response.text == content


@pytest.mark.parametrize(
    ["status", "attempts"],
    [
        (400, 0),
        (401, 0),
        (403, 0),
        (404, 0),
        (429, 5),
        (500, 5),
        (501, 5),
        (502, 5),
        (503, 5),
        (504, 5),
    ],
)
def test_authenticator_request_retries_on_status_code(
    mocker: MockerFixture,
    config: Config,
    http: type[httpretty.httpretty],
    status: int,
    attempts: int,
) -> None:
    sleep = mocker.patch("time.sleep")
    sdist_uri = f"https://foo.bar/files/{uuid.uuid4()!s}/foo-0.1.0.tar.gz"
    content = str(uuid.uuid4())

    def callback(
        request: requests.Request, uri: str, response_headers: dict[str, str]
    ) -> list[int | dict[str, str] | str]:
        return [status, response_headers, content]

    http.register_uri(httpretty.GET, sdist_uri, body=callback)
    authenticator = Authenticator(config, NullIO())

    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        authenticator.request("get", sdist_uri)

    assert excinfo.value.response is not None
    assert excinfo.value.response.status_code == status
    assert excinfo.value.response.text == content

    assert sleep.call_count == attempts


def test_authenticator_uses_env_provided_credentials(
    config: Config,
    repo: dict[str, dict[str, str]],
    environ: None,
    mock_remote: type[httpretty.httpretty],
    http: type[httpretty.httpretty],
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("POETRY_HTTP_BASIC_FOO_USERNAME", "bar")
    monkeypatch.setenv("POETRY_HTTP_BASIC_FOO_PASSWORD", "baz")

    config.merge({"repositories": repo})

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.last_request()

    basic_auth = base64.b64encode(b"bar:baz").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


@pytest.mark.parametrize(
    "cert,client_cert",
    [
        (None, None),
        (None, "path/to/provided/client-cert"),
        ("/path/to/provided/cert", None),
        ("/path/to/provided/cert", "path/to/provided/client-cert"),
    ],
)
def test_authenticator_uses_certs_from_config_if_not_provided(
    config: Config,
    mock_remote: type[httpretty.httpretty],
    mock_config: Config,
    http: type[httpretty.httpretty],
    mocker: MockerFixture,
    cert: str | None,
    client_cert: str | None,
) -> None:
    configured_cert = "/path/to/cert"
    configured_client_cert = "/path/to/client-cert"

    mock_config.merge(
        {
            "certificates": {
                "foo": {"cert": configured_cert, "client-cert": configured_client_cert}
            },
        }
    )

    authenticator = Authenticator(mock_config, NullIO())
    url = "https://foo.bar/files/foo-0.1.0.tar.gz"
    session = authenticator.get_session(url)
    session_send = mocker.patch.object(session, "send")
    authenticator.request(
        "get",
        url,
        verify=cert,
        cert=client_cert,
    )
    kwargs = session_send.call_args[1]

    assert Path(kwargs["verify"]) == Path(cert or configured_cert)
    assert Path(kwargs["cert"]) == Path(client_cert or configured_client_cert)


def test_authenticator_uses_credentials_from_config_matched_by_url_path(
    config: Config, mock_remote: None, http: type[httpretty.httpretty]
) -> None:
    config.merge(
        {
            "repositories": {
                "foo-alpha": {"url": "https://foo.bar/alpha/files/simple/"},
                "foo-beta": {"url": "https://foo.bar/beta/files/simple/"},
            },
            "http-basic": {
                "foo-alpha": {"username": "bar", "password": "alpha"},
                "foo-beta": {"username": "baz", "password": "beta"},
            },
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/alpha/files/simple/foo-0.1.0.tar.gz")

    request = http.last_request()

    basic_auth = base64.b64encode(b"bar:alpha").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"

    # Make request on second repository with the same netloc but different credentials
    authenticator.request("get", "https://foo.bar/beta/files/simple/foo-0.1.0.tar.gz")

    request = http.last_request()

    basic_auth = base64.b64encode(b"baz:beta").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_uses_credentials_from_config_with_at_sign_in_path(
    config: Config, mock_remote: None, http: type[httpretty.httpretty]
) -> None:
    config.merge(
        {
            "repositories": {
                "foo": {"url": "https://foo.bar/beta/files/simple/"},
            },
            "http-basic": {
                "foo": {"username": "bar", "password": "baz"},
            },
        }
    )
    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/beta/files/simple/f@@-0.1.0.tar.gz")

    request = http.last_request()

    basic_auth = base64.b64encode(b"bar:baz").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_falls_back_to_keyring_url_matched_by_path(
    config: Config,
    mock_remote: None,
    http: type[httpretty.httpretty],
    with_simple_keyring: None,
    dummy_keyring: DummyBackend,
) -> None:
    config.merge(
        {
            "repositories": {
                "foo-alpha": {"url": "https://foo.bar/alpha/files/simple/"},
                "foo-beta": {"url": "https://foo.bar/beta/files/simple/"},
            }
        }
    )

    dummy_keyring.set_password(
        "https://foo.bar/alpha/files/simple/", None, SimpleCredential("foo", "bar")
    )
    dummy_keyring.set_password(
        "https://foo.bar/beta/files/simple/", None, SimpleCredential("foo", "baz")
    )

    authenticator = Authenticator(config, NullIO())

    authenticator.request("get", "https://foo.bar/alpha/files/simple/foo-0.1.0.tar.gz")
    request = http.last_request()

    basic_auth = base64.b64encode(b"foo:bar").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"

    authenticator.request("get", "https://foo.bar/beta/files/simple/foo-0.1.0.tar.gz")
    request = http.last_request()

    basic_auth = base64.b64encode(b"foo:baz").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_uses_env_provided_credentials_matched_by_url_path(
    config: Config,
    environ: None,
    mock_remote: type[httpretty.httpretty],
    http: type[httpretty.httpretty],
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("POETRY_HTTP_BASIC_FOO_ALPHA_USERNAME", "bar")
    monkeypatch.setenv("POETRY_HTTP_BASIC_FOO_ALPHA_PASSWORD", "alpha")
    monkeypatch.setenv("POETRY_HTTP_BASIC_FOO_BETA_USERNAME", "baz")
    monkeypatch.setenv("POETRY_HTTP_BASIC_FOO_BETA_PASSWORD", "beta")

    config.merge(
        {
            "repositories": {
                "foo-alpha": {"url": "https://foo.bar/alpha/files/simple/"},
                "foo-beta": {"url": "https://foo.bar/beta/files/simple/"},
            }
        }
    )

    authenticator = Authenticator(config, NullIO())

    authenticator.request("get", "https://foo.bar/alpha/files/simple/foo-0.1.0.tar.gz")
    request = http.last_request()

    basic_auth = base64.b64encode(b"bar:alpha").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"

    authenticator.request("get", "https://foo.bar/beta/files/simple/foo-0.1.0.tar.gz")
    request = http.last_request()

    basic_auth = base64.b64encode(b"baz:beta").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_azure_feed_guid_credentials(
    config: Config,
    mock_remote: None,
    http: type[httpretty.httpretty],
    with_simple_keyring: None,
    dummy_keyring: DummyBackend,
) -> None:
    config.merge(
        {
            "repositories": {
                "alpha": {
                    "url": "https://foo.bar/org-alpha/_packaging/feed/pypi/simple/"
                },
                "beta": {
                    "url": "https://foo.bar/org-beta/_packaging/feed/pypi/simple/"
                },
            },
            "http-basic": {
                "alpha": {"username": "foo", "password": "bar"},
                "beta": {"username": "baz", "password": "qux"},
            },
        }
    )

    authenticator = Authenticator(config, NullIO())

    authenticator.request(
        "get",
        "https://foo.bar/org-alpha/_packaging/GUID/pypi/simple/a/1.0.0/a-1.0.0.whl",
    )
    request = http.last_request()

    basic_auth = base64.b64encode(b"foo:bar").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"

    authenticator.request(
        "get",
        "https://foo.bar/org-beta/_packaging/GUID/pypi/simple/b/1.0.0/a-1.0.0.whl",
    )
    request = http.last_request()

    basic_auth = base64.b64encode(b"baz:qux").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_add_repository(
    config: Config,
    mock_remote: None,
    http: type[httpretty.httpretty],
    with_simple_keyring: None,
    dummy_keyring: DummyBackend,
) -> None:
    config.merge(
        {
            "http-basic": {
                "source": {"username": "foo", "password": "bar"},
            },
        }
    )

    authenticator = Authenticator(config, NullIO())

    authenticator.request(
        "get",
        "https://foo.bar/simple/a/1.0.0/a-1.0.0.whl",
    )
    request = http.last_request()
    assert "Authorization" not in request.headers

    authenticator.add_repository("source", "https://foo.bar/simple/")

    authenticator.request(
        "get",
        "https://foo.bar/simple/a/1.0.0/a-1.0.0.whl",
    )
    request = http.last_request()

    basic_auth = base64.b64encode(b"foo:bar").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_git_repositories(
    config: Config,
    mock_remote: None,
    http: type[httpretty.httpretty],
    with_simple_keyring: None,
    dummy_keyring: DummyBackend,
) -> None:
    config.merge(
        {
            "repositories": {
                "one": {"url": "https://foo.bar/org/one.git"},
                "two": {"url": "https://foo.bar/org/two.git"},
            },
            "http-basic": {
                "one": {"username": "foo", "password": "bar"},
                "two": {"username": "baz", "password": "qux"},
            },
        }
    )

    authenticator = Authenticator(config, NullIO())

    one = authenticator.get_credentials_for_git_url("https://foo.bar/org/one.git")
    assert one.username == "foo"
    assert one.password == "bar"

    two = authenticator.get_credentials_for_git_url("https://foo.bar/org/two.git")
    assert two.username == "baz"
    assert two.password == "qux"

    two_ssh = authenticator.get_credentials_for_git_url("ssh://git@foo.bar/org/two.git")
    assert not two_ssh.username
    assert not two_ssh.password

    three = authenticator.get_credentials_for_git_url("https://foo.bar/org/three.git")
    assert not three.username
    assert not three.password


@pytest.mark.parametrize(
    ("ca_cert", "client_cert", "result"),
    [
        (None, None, RepositoryCertificateConfig()),
        (
            "path/to/ca.pem",
            "path/to/client.pem",
            RepositoryCertificateConfig(
                Path("path/to/ca.pem"), Path("path/to/client.pem")
            ),
        ),
        (
            None,
            "path/to/client.pem",
            RepositoryCertificateConfig(None, Path("path/to/client.pem")),
        ),
        (
            "path/to/ca.pem",
            None,
            RepositoryCertificateConfig(Path("path/to/ca.pem"), None),
        ),
        (True, None, RepositoryCertificateConfig()),
        (False, None, RepositoryCertificateConfig(verify=False)),
        (
            False,
            "path/to/client.pem",
            RepositoryCertificateConfig(None, Path("path/to/client.pem"), verify=False),
        ),
    ],
)
def test_repository_certificate_configuration_create(
    ca_cert: str | bool | None,
    client_cert: str | None,
    result: RepositoryCertificateConfig,
    config: Config,
) -> None:
    cert_config = {}

    if ca_cert is not None:
        cert_config["cert"] = ca_cert

    if client_cert is not None:
        cert_config["client-cert"] = client_cert

    config.merge({"certificates": {"foo": cert_config}})

    assert RepositoryCertificateConfig.create("foo", config) == result
