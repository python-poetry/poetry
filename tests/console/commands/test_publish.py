from __future__ import annotations

import shutil

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest
import requests

from poetry.factory import Factory
from poetry.publishing.uploader import UploadError


if TYPE_CHECKING:
    import httpretty

    from cleo.testers.application_tester import ApplicationTester
    from pytest_mock import MockerFixture

    from poetry.utils.env import VirtualEnv
    from tests.helpers import PoetryTestApplication
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter


def test_publish_not_possible_in_non_package_mode(
    fixture_dir: FixtureDirGetter,
    command_tester_factory: CommandTesterFactory,
) -> None:
    source_dir = fixture_dir("non_package_mode")

    poetry = Factory().create_poetry(source_dir)
    tester = command_tester_factory("publish", poetry)

    assert tester.execute() == 1
    assert (
        tester.io.fetch_error()
        == "Publishing a package is not possible in non-package mode.\n"
    )


def test_publish_returns_non_zero_code_for_upload_errors(
    app: PoetryTestApplication,
    app_tester: ApplicationTester,
    http: type[httpretty.httpretty],
) -> None:
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
) -> None:
    def request_callback(*_: Any, **__: Any) -> None:
        raise requests.ConnectionError()

    http.register_uri(
        http.POST, "https://upload.pypi.org/legacy/", body=request_callback
    )

    exit_code = app_tester.execute("publish --username foo --password bar")

    assert exit_code == 1

    expected = str(UploadError(error=requests.ConnectionError()))

    assert expected in app_tester.io.fetch_error()


def test_publish_with_cert(
    app_tester: ApplicationTester, mocker: MockerFixture
) -> None:
    publisher_publish = mocker.patch("poetry.publishing.Publisher.publish")

    app_tester.execute("publish --cert path/to/ca.pem")

    assert [
        (None, None, None, Path("path/to/ca.pem"), None, False, False)
    ] == publisher_publish.call_args


def test_publish_with_client_cert(
    app_tester: ApplicationTester, mocker: MockerFixture
) -> None:
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
) -> None:
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
) -> None:
    http.register_uri(
        http.POST, "https://upload.pypi.org/legacy/", status=409, body="Conflict"
    )

    exit_code = app_tester.execute(
        "publish --skip-existing --username foo --password bar"
    )

    assert exit_code == 0

    error = app_tester.io.fetch_error()
    assert "- Uploading simple_project-1.2.3.tar.gz File exists. Skipping" in error


@pytest.mark.parametrize("dist_dir", [None, "dist", "other_dist/dist", "absolute"])
def test_publish_dist_dir_option(
    http: type[httpretty.httpretty],
    fixture_dir: FixtureDirGetter,
    tmp_path: Path,
    tmp_venv: VirtualEnv,
    command_tester_factory: CommandTesterFactory,
    dist_dir: str | None,
) -> None:
    source_dir = fixture_dir("with_multiple_dist_dir")
    target_dir = tmp_path / "project"
    shutil.copytree(str(source_dir), str(target_dir))

    http.register_uri(
        http.POST, "https://upload.pypi.org/legacy/", status=409, body="Conflict"
    )

    poetry = Factory().create_poetry(target_dir)
    tester = command_tester_factory("publish", poetry, environment=tmp_venv)

    if dist_dir is None:
        exit_code = tester.execute("--dry-run")
    elif dist_dir == "absolute":
        exit_code = tester.execute(f"--dist-dir {target_dir / 'dist'} --dry-run")
    else:
        exit_code = tester.execute(f"--dist-dir {dist_dir} --dry-run")

    assert exit_code == 0

    output = tester.io.fetch_output()
    error = tester.io.fetch_error()

    assert "Publishing simple-project (1.2.3) to PyPI" in output
    assert "- Uploading simple_project-1.2.3.tar.gz" in error
    assert "- Uploading simple_project-1.2.3-py2.py3-none-any.whl" in error


@pytest.mark.parametrize("dist_dir", ["../dist", "tmp/dist", "absolute"])
def test_publish_dist_dir_and_build_options(
    http: type[httpretty.httpretty],
    fixture_dir: FixtureDirGetter,
    tmp_path: Path,
    tmp_venv: VirtualEnv,
    command_tester_factory: CommandTesterFactory,
    dist_dir: str | None,
) -> None:
    source_dir = fixture_dir("simple_project")
    target_dir = tmp_path / "project"
    shutil.copytree(str(source_dir), str(target_dir))

    # Remove dist dir because as it will be built again
    shutil.rmtree(target_dir / "dist")

    http.register_uri(
        http.POST, "https://upload.pypi.org/legacy/", status=409, body="Conflict"
    )

    poetry = Factory().create_poetry(target_dir)
    tester = command_tester_factory("publish", poetry, environment=tmp_venv)

    if dist_dir == "absolute":
        exit_code = tester.execute(
            f"--dist-dir {target_dir / 'test/dist'} --dry-run --build"
        )
    else:
        exit_code = tester.execute(f"--dist-dir {dist_dir} --dry-run --build")

    assert exit_code == 0

    output = tester.io.fetch_output()
    error = tester.io.fetch_error()

    assert "Publishing simple-project (1.2.3) to PyPI" in output
    assert "- Uploading simple_project-1.2.3.tar.gz" in error
    assert "- Uploading simple_project-1.2.3-py2.py3-none-any.whl" in error
