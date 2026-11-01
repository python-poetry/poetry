from __future__ import annotations

import base64
import logging
import re
import uuid

from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NoReturn

import pytest
import requests
import responses

from cleo.io.null_io import NullIO
from keyring.credentials import SimpleCredential

from poetry.console.exceptions import PoetryRuntimeError
from poetry.utils.authenticator import Authenticator
from poetry.utils.authenticator import AuthenticatorRepositoryConfig
from poetry.utils.authenticator import RepositoryCertificateConfig
from poetry.utils.password_manager import PoetryKeyring


if TYPE_CHECKING:
    from pytest import LogCaptureFixture
    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture

    from tests.conftest import Config
    from tests.conftest import DummyBackend
    from tests.types import HttpResponse


@pytest.fixture()
def mock_remote(http: responses.RequestsMock) -> None:
    http.get(
        re.compile(r"^https?://(?:[^@]+@)?foo\.bar/(.+?)$"),
        body="",
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
    mock_config: Config, mock_remote: None, http: responses.RequestsMock
) -> None:
    authenticator = Authenticator(mock_config, NullIO())
    authenticator.request("get", "https://foo001:bar002@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.calls[-1].request
    basic_auth = base64.b64encode(b"foo001:bar002").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_uses_credentials_from_config_if_not_provided(
    mock_config: Config, mock_remote: None, http: responses.RequestsMock
) -> None:
    authenticator = Authenticator(mock_config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.calls[-1].request
    basic_auth = base64.b64encode(b"bar:baz").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_does_not_send_https_credentials_over_http(
    mock_config: Config,
    mock_remote: None,
    http: responses.RequestsMock,
    with_simple_keyring: None,
) -> None:
    authenticator = Authenticator(mock_config, NullIO())
    authenticator.request("get", "http://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.calls[-1].request
    assert "Authorization" not in request.headers


@pytest.mark.parametrize("repo", [{"foo": {"url": "http://foo.bar/simple/"}}])
def test_authenticator_sends_http_credentials_over_https(
    mock_config: Config, mock_remote: None, http: responses.RequestsMock
) -> None:
    authenticator = Authenticator(mock_config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.calls[-1].request
    basic_auth = base64.b64encode(b"bar:baz").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_uses_username_only_credentials(
    mock_config: Config,
    mock_remote: None,
    http: responses.RequestsMock,
    with_simple_keyring: None,
) -> None:
    authenticator = Authenticator(mock_config, NullIO())
    authenticator.request("get", "https://foo001@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.calls[-1].request
    basic_auth = base64.b64encode(b"foo001:").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_ignores_locked_keyring(
    mock_remote: None,
    http: responses.RequestsMock,
    with_locked_keyring: None,
    caplog: LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger="poetry.utils.password_manager")
    spy_get_credential = mocker.spy(PoetryKeyring, "get_credential")
    spy_get_password = mocker.spy(PoetryKeyring, "get_password")
    authenticator = Authenticator()
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.calls[-1].request
    assert "Authorization" not in request.headers
    assert "Accessing keyring failed during availability check" in caplog.messages
    assert "Using keyring backend 'conftest LockedBackend'" in caplog.messages
    assert spy_get_credential.call_count == spy_get_password.call_count == 0


def test_authenticator_ignores_failing_keyring(
    mock_remote: None,
    http: responses.RequestsMock,
    with_erroneous_keyring: None,
    caplog: LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger="poetry.utils.password_manager")
    spy_get_credential = mocker.spy(PoetryKeyring, "get_credential")
    spy_get_password = mocker.spy(PoetryKeyring, "get_password")
    authenticator = Authenticator()
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.calls[-1].request
    assert "Authorization" not in request.headers

    assert "Using keyring backend 'conftest ErroneousBackend'" in caplog.messages
    assert "Accessing keyring failed during availability check" in caplog.messages
    assert spy_get_credential.call_count == spy_get_password.call_count == 0


def test_authenticator_uses_password_only_credentials(
    mock_config: Config, mock_remote: None, http: responses.RequestsMock
) -> None:
    authenticator = Authenticator(mock_config, NullIO())
    authenticator.request("get", "https://:bar002@foo.bar/files/foo-0.1.0.tar.gz")

    request = http.calls[-1].request
    basic_auth = base64.b64encode(b":bar002").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_uses_empty_strings_as_default_password(
    config: Config,
    mock_remote: None,
    repo: dict[str, dict[str, str]],
    http: responses.RequestsMock,
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

    request = http.calls[-1].request
    basic_auth = base64.b64encode(b"bar:").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_does_not_ignore_empty_strings_as_default_username(
    config: Config,
    mock_remote: None,
    repo: dict[str, dict[str, str]],
    http: responses.RequestsMock,
) -> None:
    config.merge(
        {
            "repositories": repo,
            "http-basic": {"foo": {"username": None, "password": "bar"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.calls[-1].request
    basic_auth = base64.b64encode(b":bar").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_falls_back_to_keyring_url(
    config: Config,
    mock_remote: None,
    repo: dict[str, dict[str, str]],
    http: responses.RequestsMock,
    with_simple_keyring: None,
    dummy_keyring: DummyBackend,
) -> None:
    config.merge(
        {
            "repositories": repo,
        }
    )

    dummy_keyring.set_default_service_credential(
        "https://foo.bar/simple/",
        SimpleCredential("foo", "bar"),
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.calls[-1].request
    basic_auth = base64.b64encode(b"foo:bar").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_falls_back_to_keyring_netloc(
    config: Config,
    mock_remote: None,
    repo: dict[str, dict[str, str]],
    http: responses.RequestsMock,
    with_simple_keyring: None,
    dummy_keyring: DummyBackend,
    poetry_keyring: PoetryKeyring,
) -> None:
    config.merge(
        {
            "repositories": repo,
        }
    )

    dummy_keyring.set_default_service_credential(
        "foo.bar",
        SimpleCredential("foo", "bar"),
    )

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.calls[-1].request
    basic_auth = base64.b64encode(b"foo:bar").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_authenticator_request_retries_on_exception(
    mocker: MockerFixture, config: Config, http: responses.RequestsMock
) -> None:
    sleep = mocker.patch("time.sleep")
    sdist_uri = f"https://foo.bar/files/{uuid.uuid4()!s}/foo-0.1.0.tar.gz"
    content = str(uuid.uuid4())
    seen: list[str] = []

    def callback(request: requests.PreparedRequest) -> HttpResponse:
        assert request.url
        if seen.count(request.url) < 2:
            seen.append(request.url)
            raise requests.exceptions.ConnectionError("Disconnected")
        return 200, {}, content

    http.add_callback(responses.GET, sdist_uri, callback=callback)

    authenticator = Authenticator(config, NullIO())
    response = authenticator.request("get", sdist_uri)
    assert response.text == content
    assert sleep.call_count == 2


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_authenticator_request_raises_exception_when_attempts_exhausted(
    mocker: MockerFixture, config: Config, http: responses.RequestsMock
) -> None:
    sleep = mocker.patch("time.sleep")
    sdist_uri = f"https://foo.bar/files/{uuid.uuid4()!s}/foo-0.1.0.tar.gz"

    def callback(request: requests.PreparedRequest) -> NoReturn:
        raise requests.exceptions.ConnectionError(str(uuid.uuid4()))

    http.add_callback(responses.GET, sdist_uri, callback=callback)
    authenticator = Authenticator(config, NullIO())

    with pytest.raises(PoetryRuntimeError) as e:
        authenticator.request("get", sdist_uri)

    assert str(e.value) == "All attempts to connect to foo.bar failed."
    assert sleep.call_count == 5


def test_authenticator_request_respects_retry_header(
    mocker: MockerFixture,
    config: Config,
    http: responses.RequestsMock,
) -> None:
    sleep = mocker.patch("time.sleep")
    sdist_uri = f"https://foo.bar/files/{uuid.uuid4()!s}/foo-0.1.0.tar.gz"
    content = str(uuid.uuid4())
    seen: list[str] = []

    def callback(request: requests.PreparedRequest) -> HttpResponse:
        assert request.url
        if not seen.count(request.url):
            seen.append(request.url)
            return 429, {"Retry-After": "42"}, "Retry later"

        return 200, {}, content

    http.add_callback(responses.GET, sdist_uri, callback=callback)
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
    http: responses.RequestsMock,
    status: int,
    attempts: int,
) -> None:
    sleep = mocker.patch("time.sleep")
    sdist_uri = f"https://foo.bar/files/{uuid.uuid4()!s}/foo-0.1.0.tar.gz"
    content = str(uuid.uuid4())

    def callback(request: requests.PreparedRequest) -> HttpResponse:
        return status, {}, content

    http.add_callback(responses.GET, sdist_uri, callback=callback)
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
    mock_remote: responses.RequestsMock,
    http: responses.RequestsMock,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("POETRY_HTTP_BASIC_FOO_USERNAME", "bar")
    monkeypatch.setenv("POETRY_HTTP_BASIC_FOO_PASSWORD", "baz")

    config.merge({"repositories": repo})

    authenticator = Authenticator(config, NullIO())
    authenticator.request("get", "https://foo.bar/files/foo-0.1.0.tar.gz")

    request = http.calls[-1].request

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
    mock_remote: responses.RequestsMock,
    mock_config: Config,
    http: responses.RequestsMock,
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


@pytest.mark.parametrize("verify", [True, False, None])
def test_authenticator_request_verify_is_respected(
    config: Config,
    mock_remote: responses.RequestsMock,
    mock_config: Config,
    http: responses.RequestsMock,
    mocker: MockerFixture,
    verify: bool | None,
) -> None:
    """especially verify=False must not be overridden by configured certificates."""
    mock_config.merge(
        {
            "certificates": {
                "foo": {"cert": "/path/to/cert", "client-cert": "/path/to/client-cert"}
            },
        }
    )

    authenticator = Authenticator(mock_config, NullIO())
    url = "https://foo.bar/files/foo-0.1.0.tar.gz"
    session = authenticator.get_session(url)
    session_send = mocker.patch.object(session, "send")
    authenticator.request("get", url, verify=verify)
    kwargs = session_send.call_args[1]

    if verify is None:
        assert kwargs["verify"] == str(Path("/path/to/cert"))
    else:
        assert kwargs["verify"] is verify


def test_authenticator_uses_credentials_from_config_matched_by_url_path(
    config: Config, mock_remote: None, http: responses.RequestsMock
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

    request = http.calls[-1].request

    basic_auth = base64.b64encode(b"bar:alpha").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"

    # Make request on second repository with the same netloc but different credentials
    authenticator.request("get", "https://foo.bar/beta/files/simple/foo-0.1.0.tar.gz")

    request = http.calls[-1].request

    basic_auth = base64.b64encode(b"baz:beta").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_uses_credentials_from_config_with_at_sign_in_path(
    config: Config, mock_remote: None, http: responses.RequestsMock
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

    request = http.calls[-1].request

    basic_auth = base64.b64encode(b"bar:baz").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_falls_back_to_keyring_url_matched_by_path(
    config: Config,
    mock_remote: None,
    http: responses.RequestsMock,
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

    dummy_keyring.set_default_service_credential(
        "https://foo.bar/alpha/files/simple/",
        SimpleCredential("foo", "bar"),
    )
    dummy_keyring.set_default_service_credential(
        "https://foo.bar/beta/files/simple/",
        SimpleCredential("foo", "baz"),
    )

    authenticator = Authenticator(config, NullIO())

    authenticator.request("get", "https://foo.bar/alpha/files/simple/foo-0.1.0.tar.gz")
    request = http.calls[-1].request

    basic_auth = base64.b64encode(b"foo:bar").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"

    authenticator.request("get", "https://foo.bar/beta/files/simple/foo-0.1.0.tar.gz")
    request = http.calls[-1].request

    basic_auth = base64.b64encode(b"foo:baz").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_uses_env_provided_credentials_matched_by_url_path(
    config: Config,
    environ: None,
    mock_remote: responses.RequestsMock,
    http: responses.RequestsMock,
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
    request = http.calls[-1].request

    basic_auth = base64.b64encode(b"bar:alpha").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"

    authenticator.request("get", "https://foo.bar/beta/files/simple/foo-0.1.0.tar.gz")
    request = http.calls[-1].request

    basic_auth = base64.b64encode(b"baz:beta").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


@pytest.mark.parametrize(
    ("repository_path", "request_path", "expected"),
    [
        ("/repo/private", "/repo/private/pkg.whl", (2, True)),
        ("/repo/private/", "/repo/private/pkg.whl", (2, True)),
        ("/repo/private", "/repo/private", (2, True)),
        ("/repo/private", "/repo/private/", (2, True)),
        # textual prefixes are not path matches
        ("/repo/private", "/repo/private2/pkg.whl", (1, False)),
        ("/repo/private", "/repo/private-ns/pkg.whl", (1, False)),
        ("/repo/private", "/repo/priv/pkg.whl", (1, False)),
        ("/repo/priv", "/repo/private/pkg.whl", (1, False)),
        # partially shared paths (e.g. Azure feed GUIDs) still count shared segments
        ("/org/_packaging/feed/pypi/simple/", "/org/_packaging/GUID/x.whl", (2, False)),
        ("/simple/", "/files/pkg.whl", (0, False)),
        ("/", "/files/pkg.whl", (0, True)),
        ("", "/files/pkg.whl", (0, True)),
    ],
)
def test_repository_config_path_match_key(
    repository_path: str, request_path: str, expected: tuple[int, bool]
) -> None:
    repository = AuthenticatorRepositoryConfig(
        "repo", f"https://foo.bar{repository_path}"
    )
    assert repository.path_match_key(request_path) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://foo.bar/repo/private/pkg.whl", "private"),
        ("https://foo.bar/repo/private2/pkg.whl", "private2"),
        ("https://foo.bar/repo/private-ns/pkg.whl", "private-ns"),
        # "/repo/private" shares as many characters with this url as "/repo/priv",
        # but only "/repo/priv" matches on whole path segments
        ("https://foo.bar/repo/priv/pkg.whl", "priv"),
        # a repository containing the url beats one merely sharing its segments
        ("https://foo.bar/repo/priv/sub/pkg.whl", "priv"),
        # the most specific repository wins for nested paths
        ("https://foo.bar/repo/priv/deeper/pkg.whl", "deeper"),
        # credentials stay scoped to the host: urls outside every repository path
        # fall back to the first configured repository on that host
        ("https://foo.bar/files/pkg.whl", "private"),
        ("https://other.host/repo/private/pkg.whl", None),
    ],
)
def test_authenticator_matches_repository_by_whole_path_segments(
    config: Config, url: str, expected: str | None
) -> None:
    # deliberately ordered so that textual prefix matching picks the wrong one
    config.merge(
        {
            "repositories": {
                "private": {"url": "https://foo.bar/repo/private"},
                "priv": {"url": "https://foo.bar/repo/priv"},
                "private2": {"url": "https://foo.bar/repo/private2/"},
                "private-ns": {"url": "https://foo.bar/repo/private-ns/"},
                "deeper": {"url": "https://foo.bar/repo/priv/deeper/"},
            },
        }
    )

    authenticator = Authenticator(config, NullIO())
    repository = authenticator.get_repository_config_for_url(url)

    assert (repository.name if repository else None) == expected


def test_authenticator_does_not_send_sibling_repository_credentials(
    config: Config, mock_remote: None, http: responses.RequestsMock
) -> None:
    config.merge(
        {
            "repositories": {
                "private": {"url": "https://foo.bar/repo/private"},
                "priv": {"url": "https://foo.bar/repo/priv"},
            },
            "http-basic": {
                "private": {"username": "alice", "password": "secret"},
                "priv": {"username": "bob", "password": "other-secret"},
            },
        }
    )

    authenticator = Authenticator(config, NullIO())

    authenticator.request("get", "https://foo.bar/repo/priv/pkg.whl")
    request = http.calls[-1].request
    basic_auth = base64.b64encode(b"bob:other-secret").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"

    authenticator.request("get", "https://foo.bar/repo/private/pkg.whl")
    request = http.calls[-1].request
    basic_auth = base64.b64encode(b"alice:secret").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_azure_feed_guid_credentials(
    config: Config,
    mock_remote: None,
    http: responses.RequestsMock,
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
    request = http.calls[-1].request

    basic_auth = base64.b64encode(b"foo:bar").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"

    authenticator.request(
        "get",
        "https://foo.bar/org-beta/_packaging/GUID/pypi/simple/b/1.0.0/a-1.0.0.whl",
    )
    request = http.calls[-1].request

    basic_auth = base64.b64encode(b"baz:qux").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_add_repository(
    config: Config,
    mock_remote: None,
    http: responses.RequestsMock,
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
    request = http.calls[-1].request
    assert "Authorization" not in request.headers

    authenticator.add_repository("source", "https://foo.bar/simple/")

    authenticator.request(
        "get",
        "https://foo.bar/simple/a/1.0.0/a-1.0.0.whl",
    )
    request = http.calls[-1].request

    basic_auth = base64.b64encode(b"foo:bar").decode()
    assert request.headers["Authorization"] == f"Basic {basic_auth}"


def test_authenticator_git_repositories(
    config: Config,
    mock_remote: None,
    http: responses.RequestsMock,
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
    ("repository_url", "git_url", "expect_credentials"),
    [
        ("https://foo.bar/org/one.git", "https://foo.bar/org/one.git", True),
        # same path on another host must not receive the credentials
        ("https://foo.bar/org/one.git", "https://evil.example/org/one.git", False),
        ("https://foo.bar/org/one.git", "https://foo.bar:8443/org/one.git", False),
        ("https://foo.bar/simple/", "https://evil.example/simple/", False),
        # credentials configured for https must not be sent in the clear
        ("https://foo.bar/org/one.git", "http://foo.bar/org/one.git", False),
        ("http://foo.bar/org/one.git", "http://foo.bar/org/one.git", True),
        ("http://foo.bar/org/one.git", "https://foo.bar/org/one.git", True),
    ],
)
def test_authenticator_git_repositories_match_host_and_scheme(
    config: Config,
    mock_remote: None,
    with_simple_keyring: None,
    dummy_keyring: DummyBackend,
    repository_url: str,
    git_url: str,
    expect_credentials: bool,
) -> None:
    config.merge(
        {
            "repositories": {"one": {"url": repository_url}},
            "http-basic": {"one": {"username": "foo", "password": "bar"}},
        }
    )

    authenticator = Authenticator(config, NullIO())
    credentials = authenticator.get_credentials_for_git_url(git_url)

    if expect_credentials:
        assert credentials.username == "foo"
        assert credentials.password == "bar"
    else:
        assert not credentials.username
        assert not credentials.password


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


@pytest.fixture
def netrc(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    """Point requests to a netrc file that exists only once a test writes to it."""
    netrc_file = tmp_path / "netrc"
    monkeypatch.setenv("NETRC", str(netrc_file))
    return netrc_file


def write_netrc(netrc_file: Path, host: str) -> None:
    netrc_file.touch(mode=0o600)
    netrc_file.write_text(
        f"machine {host} login netrcuser password netrcpw\n", encoding="utf-8"
    )


def basic_auth_per_hop(http: responses.RequestsMock) -> list[str | None]:
    headers = [call.request.headers.get("Authorization") for call in http.calls]
    return [
        base64.b64decode(header.split()[1]).decode() if header else None
        for header in headers
    ]


@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_authenticator_keeps_configured_credentials_on_same_host_redirect(
    mock_config: Config, netrc: Path, http: responses.RequestsMock, status: int
) -> None:
    write_netrc(netrc, "foo.bar")
    http.get(
        "https://foo.bar/simple",
        status=status,
        headers={"Location": "https://foo.bar/simple/"},
    )
    http.get("https://foo.bar/simple/")

    Authenticator(mock_config, NullIO()).request("get", "https://foo.bar/simple")

    assert basic_auth_per_hop(http) == ["bar:baz", "bar:baz"]


def test_authenticator_uses_netrc_on_redirect_without_configured_credentials(
    config: Config, netrc: Path, http: responses.RequestsMock
) -> None:
    write_netrc(netrc, "foo.bar")
    http.get(
        "https://foo.bar/simple",
        status=301,
        headers={"Location": "https://foo.bar/simple/"},
    )
    http.get("https://foo.bar/simple/")

    Authenticator(config, NullIO()).request("get", "https://foo.bar/simple")

    assert basic_auth_per_hop(http) == ["netrcuser:netrcpw", "netrcuser:netrcpw"]


@pytest.mark.parametrize(
    ("netrc_host", "expected"),
    [
        (None, None),
        ("cdn.example", "netrcuser:netrcpw"),
    ],
)
def test_authenticator_drops_credentials_on_cross_host_redirect(
    mock_config: Config,
    netrc: Path,
    http: responses.RequestsMock,
    netrc_host: str | None,
    expected: str | None,
) -> None:
    if netrc_host:
        write_netrc(netrc, netrc_host)
    http.get(
        "https://foo.bar/simple",
        status=302,
        headers={"Location": "https://cdn.example/f"},
    )
    http.get("https://cdn.example/f")

    Authenticator(mock_config, NullIO()).request("get", "https://foo.bar/simple")

    assert basic_auth_per_hop(http) == ["bar:baz", expected]


@pytest.mark.parametrize(
    ("credentials", "expected"),
    [
        ({"username": "other", "password": "secret"}, "other:secret"),
        ({"username": "other"}, "other:"),
        ({"password": "secret"}, ":secret"),
    ],
)
def test_authenticator_uses_target_credentials_on_cross_host_redirect(
    mock_config: Config,
    netrc: Path,
    http: responses.RequestsMock,
    with_simple_keyring: None,
    credentials: dict[str, str],
    expected: str,
) -> None:
    write_netrc(netrc, "other.example")
    mock_config.merge(
        {
            "repositories": {"other": {"url": "https://other.example/simple/"}},
            "http-basic": {"other": credentials},
        }
    )
    http.get(
        "https://foo.bar/simple",
        status=302,
        headers={"Location": "https://other.example/simple/"},
    )
    http.get("https://other.example/simple/")

    Authenticator(mock_config, NullIO()).request("get", "https://foo.bar/simple")

    assert basic_auth_per_hop(http) == ["bar:baz", expected]


def test_authenticator_scopes_credentials_to_each_host_of_a_redirect_chain(
    mock_config: Config, netrc: Path, http: responses.RequestsMock
) -> None:
    http.get(
        "https://foo.bar/simple",
        status=302,
        headers={"Location": "https://cdn.example/f"},
    )
    http.get(
        "https://cdn.example/f",
        status=302,
        headers={"Location": "https://foo.bar/files/f"},
    )
    http.get("https://foo.bar/files/f")

    Authenticator(mock_config, NullIO()).request("get", "https://foo.bar/simple")

    assert basic_auth_per_hop(http) == ["bar:baz", None, "bar:baz"]


@pytest.mark.parametrize("location", ["/simple/", "https://foo.bar/simple/"])
def test_authenticator_keeps_url_provided_credentials_on_same_host_redirect(
    mock_config: Config, netrc: Path, http: responses.RequestsMock, location: str
) -> None:
    write_netrc(netrc, "foo.bar")
    http.get(
        re.compile(r"^https://(?:[^@]+@)?foo\.bar/simple$"),
        status=301,
        headers={"Location": location},
    )
    http.get(re.compile(r"^https://(?:[^@]+@)?foo\.bar/simple/$"))

    Authenticator(mock_config, NullIO()).request("get", "https://u:p@foo.bar/simple")

    assert basic_auth_per_hop(http) == ["u:p", "u:p"]


def test_authenticator_keeps_explicit_header_on_same_host_redirect(
    config: Config, netrc: Path, http: responses.RequestsMock
) -> None:
    http.get(
        "https://foo.bar/simple",
        status=301,
        headers={"Location": "https://foo.bar/simple/"},
    )
    http.get("https://foo.bar/simple/")
    header = "Basic " + base64.b64encode(b"u:p").decode()

    Authenticator(config, NullIO()).request(
        "get", "https://foo.bar/simple", headers={"Authorization": header}
    )

    assert basic_auth_per_hop(http) == ["u:p", "u:p"]


def test_authenticator_does_not_send_https_credentials_over_http_on_redirect(
    mock_config: Config, netrc: Path, http: responses.RequestsMock
) -> None:
    http.get(
        "https://foo.bar/simple",
        status=301,
        headers={"Location": "http://foo.bar/simple/"},
    )
    http.get("http://foo.bar/simple/")

    Authenticator(mock_config, NullIO()).request("get", "https://foo.bar/simple")

    assert basic_auth_per_hop(http) == ["bar:baz", None]


@pytest.mark.parametrize(
    "hops",
    [
        ["https://foo.bar/simple", "http://foo.bar/simple/"],
        ["https://cdn.example/f", "http://foo.bar/simple/"],
        ["https://foo.bar/simple", "http://cdn.example/f", "http://foo.bar/simple/"],
    ],
)
def test_authenticator_does_not_send_keyring_credentials_over_http_on_redirect(
    config: Config,
    netrc: Path,
    repo: dict[str, dict[str, str]],
    http: responses.RequestsMock,
    with_simple_keyring: None,
    dummy_keyring: DummyBackend,
    poetry_keyring: PoetryKeyring,
    hops: list[str],
) -> None:
    config.merge({"repositories": repo})
    dummy_keyring.set_default_service_credential(
        "foo.bar", SimpleCredential("foo", "bar")
    )
    for url, location in pairwise(hops):
        http.get(url, status=302, headers={"Location": location})
    http.get(hops[-1])

    Authenticator(config, NullIO()).request("get", hops[0])

    assert not any(
        auth
        for url, auth in zip(hops, basic_auth_per_hop(http), strict=True)
        if url.startswith("http://")
    )


@pytest.mark.parametrize("repo", [{"foo": {"url": "http://foo.bar/simple/"}}])
def test_authenticator_sends_http_repository_credentials_over_http_on_redirect(
    mock_config: Config, netrc: Path, http: responses.RequestsMock
) -> None:
    http.get(
        "http://cdn.example/f",
        status=302,
        headers={"Location": "http://foo.bar/simple/"},
    )
    http.get("http://foo.bar/simple/")

    Authenticator(mock_config, NullIO()).request("get", "http://cdn.example/f")

    assert basic_auth_per_hop(http) == [None, "bar:baz"]
