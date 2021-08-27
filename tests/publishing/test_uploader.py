<<<<<<< HEAD
from typing import TYPE_CHECKING
from typing import Type
=======
from pathlib import Path
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

import pytest

from cleo.io.null_io import NullIO

from poetry.factory import Factory
from poetry.publishing.uploader import Uploader
from poetry.publishing.uploader import UploadError


<<<<<<< HEAD
if TYPE_CHECKING:
    import httpretty

    from pytest_mock import MockerFixture

    from tests.types import FixtureDirGetter


@pytest.fixture
def uploader(fixture_dir: "FixtureDirGetter") -> Uploader:
    return Uploader(Factory().create_poetry(fixture_dir("simple_project")), NullIO())


def test_uploader_properly_handles_400_errors(
    http: Type["httpretty.httpretty"], uploader: Uploader
):
=======
fixtures_dir = Path(__file__).parent.parent / "fixtures"


def project(name):
    return fixtures_dir / name


@pytest.fixture
def uploader():
    return Uploader(Factory().create_poetry(project("simple_project")), NullIO())


def test_uploader_properly_handles_400_errors(http, uploader):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    http.register_uri(http.POST, "https://foo.com", status=400, body="Bad request")

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

<<<<<<< HEAD
    assert str(e.value) == "HTTP Error 400: Bad Request"


def test_uploader_properly_handles_403_errors(
    http: Type["httpretty.httpretty"], uploader: Uploader
):
=======
    assert "HTTP Error 400: Bad Request" == str(e.value)


def test_uploader_properly_handles_403_errors(http, uploader):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    http.register_uri(http.POST, "https://foo.com", status=403, body="Unauthorized")

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

<<<<<<< HEAD
    assert str(e.value) == "HTTP Error 403: Forbidden"


def test_uploader_properly_handles_301_redirects(
    http: Type["httpretty.httpretty"], uploader: Uploader
):
=======
    assert "HTTP Error 403: Forbidden" == str(e.value)


def test_uploader_properly_handles_301_redirects(http, uploader):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    http.register_uri(http.POST, "https://foo.com", status=301, body="Redirect")

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

<<<<<<< HEAD
    assert (
        str(e.value)
        == "Redirects are not supported. Is the URL missing a trailing slash?"
    )


def test_uploader_registers_for_appropriate_400_errors(
    mocker: "MockerFixture", http: Type["httpretty.httpretty"], uploader: Uploader
):
=======
    assert "Redirects are not supported. Is the URL missing a trailing slash?" == str(
        e.value
    )


def test_uploader_registers_for_appropriate_400_errors(mocker, http, uploader):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    register = mocker.patch("poetry.publishing.uploader.Uploader._register")
    http.register_uri(
        http.POST, "https://foo.com", status=400, body="No package was ever registered"
    )

    with pytest.raises(UploadError):
        uploader.upload("https://foo.com")

<<<<<<< HEAD
    assert register.call_count == 1
=======
    assert 1 == register.call_count
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
