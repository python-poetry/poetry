from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest
import requests

from poetry.publishing.uploader import UploadError


if TYPE_CHECKING:
    import httpretty

    from cleo.testers.application_tester import ApplicationTester
    from pytest_mock import MockerFixture

    from tests.helpers import PoetryTestApplication


def test_publish_returns_non_zero_code_for_upload_errors(
    app: PoetryTestApplication,
    app_tester: ApplicationTester,
    http: type[httpretty.httpretty],
):
    http.register_uri(
        http.POST, "https://upload.pypi.org/legacy/", status=400, body="Bad Request"
    )

    exit_code = app_tester.execute("publish --username foo --password bar")

    assert exit_code == 1

    expected_output = """
Publishing simple-project (1.2.3) to PyPI
"""
    expected_error_output = """\
HTTP Error 400: Bad Request | b'Bad Request'
"""

    assert expected_output in app_tester.io.fetch_output()
    assert expected_error_output in app_tester.io.fetch_error()


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_publish_returns_non_zero_code_for_connection_errors(
    app: PoetryTestApplication,
    app_tester: ApplicationTester,
    http: type[httpretty.httpretty],
):
    def request_callback(*_: Any, **__: Any) -> None:
        raise requests.ConnectionError()

    http.register_uri(
        http.POST, "https://upload.pypi.org/legacy/", body=request_callback
    )

    exit_code = app_tester.execute("publish --username foo --password bar")

    assert exit_code == 1

    expected = str(UploadError(error=requests.ConnectionError()))

    assert expected in app_tester.io.fetch_error()


def test_publish_with_cert(app_tester: ApplicationTester, mocker: MockerFixture):
    publisher_publish = mocker.patch("poetry.publishing.Publisher.publish")

    app_tester.execute("publish --cert path/to/ca.pem")

    assert [
        (None, None, None, Path("path/to/ca.pem"), None, False, False)
    ] == publisher_publish.call_args


def test_publish_with_client_cert(app_tester: ApplicationTester, mocker: MockerFixture):
    publisher_publish = mocker.patch("poetry.publishing.Publisher.publish")

    app_tester.execute("publish --client-cert path/to/client.pem")
    assert [
        (None, None, None, None, Path("path/to/client.pem"), False, False)
    ] == publisher_publish.call_args


@pytest.mark.parametrize(
    "options",
    [
        "--dry-run",
        "--skip-existing",
        "--dry-run --skip-existing",
    ],
)
def test_publish_dry_run_skip_existing(
    app_tester: ApplicationTester, http: type[httpretty.httpretty], options: str
):
    http.register_uri(
        http.POST, "https://upload.pypi.org/legacy/", status=409, body="Conflict"
    )

    exit_code = app_tester.execute(f"publish {options} --username foo --password bar")

    assert exit_code == 0

    output = app_tester.io.fetch_output()
    error = app_tester.io.fetch_error()

    assert "Publishing simple-project (1.2.3) to PyPI" in output
    assert "- Uploading simple_project-1.2.3.tar.gz" in error
    assert "- Uploading simple_project-1.2.3-py2.py3-none-any.whl" in error


def test_skip_existing_output(
    app_tester: ApplicationTester, http: type[httpretty.httpretty]
):
    http.register_uri(
        http.POST, "https://upload.pypi.org/legacy/", status=409, body="Conflict"
    )

    exit_code = app_tester.execute(
        "publish --skip-existing --username foo --password bar"
    )

    assert exit_code == 0

    error = app_tester.io.fetch_error()
    assert "- Uploading simple_project-1.2.3.tar.gz File exists. Skipping" in error
