from pathlib import Path

import requests

from poetry.publishing.uploader import UploadError


def test_publish_returns_non_zero_code_for_upload_errors(app, app_tester, http):
    http.register_uri(
        http.POST, "https://upload.pypi.org/legacy/", status=400, body="Bad Request"
    )

    exit_code = app_tester.execute("publish --username foo --password bar")

    assert 1 == exit_code

    expected_output = """
Publishing simple-project (1.2.3) to PyPI
"""
    expected_error_output = """\
  UploadError

  HTTP Error 400: Bad Request
"""

    assert expected_output in app_tester.io.fetch_output()
    assert expected_error_output in app_tester.io.fetch_error()


def test_publish_returns_non_zero_code_for_connection_errors(app, app_tester, http):
    def request_callback(*_, **__):
        raise requests.ConnectionError()

    http.register_uri(
        http.POST, "https://upload.pypi.org/legacy/", body=request_callback
    )

    exit_code = app_tester.execute("publish --username foo --password bar")

    assert 1 == exit_code

    expected = str(UploadError(error=requests.ConnectionError()))

    assert expected in app_tester.io.fetch_error()


def test_publish_with_cert(app_tester, mocker):
    publisher_publish = mocker.patch("poetry.publishing.Publisher.publish")

    app_tester.execute("publish --cert path/to/ca.pem")

    assert [
        (None, None, None, Path("path/to/ca.pem"), None, False)
    ] == publisher_publish.call_args


def test_publish_with_client_cert(app_tester, mocker):
    publisher_publish = mocker.patch("poetry.publishing.Publisher.publish")

    app_tester.execute("publish --client-cert path/to/client.pem")
    assert [
        (None, None, None, None, Path("path/to/client.pem"), False)
    ] == publisher_publish.call_args


def test_publish_dry_run(app_tester, http):
    http.register_uri(
        http.POST, "https://upload.pypi.org/legacy/", status=403, body="Forbidden"
    )

    exit_code = app_tester.execute("publish --dry-run --username foo --password bar")

    assert 0 == exit_code

    output = app_tester.io.fetch_output()
    error = app_tester.io.fetch_error()

    assert "Publishing simple-project (1.2.3) to PyPI" in output
    assert "- Uploading simple-project-1.2.3.tar.gz" in error
    assert "- Uploading simple_project-1.2.3-py2.py3-none-any.whl" in error
