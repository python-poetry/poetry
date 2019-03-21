import httpretty
import pytest
import shutil

from poetry.masonry.publishing.uploader import UploadError
from poetry.masonry.publishing.uploader import Uploader
from poetry.io import NullIO
from poetry.poetry import Poetry
from poetry.utils._compat import Path


fixtures_dir = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def setup():
    clear_samples_dist()

    yield

    clear_samples_dist()


def clear_samples_dist():
    for dist in fixtures_dir.glob("**/dist"):
        if dist.is_dir():
            shutil.rmtree(str(dist))


def project(name):
    return Path(__file__).parent / "fixtures" / name


@httpretty.activate
def test_uploader_properly_handles_400_errors():
    httpretty.register_uri(
        httpretty.POST, "https://foo.com", status=400, body="Bad request"
    )
    uploader = Uploader(Poetry.create(project("complete")), NullIO())

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert "HTTP Error 400: Bad Request" == str(e.value)


@httpretty.activate
def test_uploader_properly_handles_403_errors():
    httpretty.register_uri(
        httpretty.POST, "https://foo.com", status=403, body="Unauthorized"
    )
    uploader = Uploader(Poetry.create(project("complete")), NullIO())

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert "HTTP Error 403: Forbidden" == str(e.value)


@httpretty.activate
def test_uploader_registers_for_appropriate_400_errors(mocker):
    register = mocker.patch("poetry.masonry.publishing.uploader.Uploader._register")
    httpretty.register_uri(
        httpretty.POST,
        "https://foo.com",
        status=400,
        body="No package was ever registered",
    )
    uploader = Uploader(Poetry.create(project("complete")), NullIO())

    with pytest.raises(UploadError):
        uploader.upload("https://foo.com")

    register.assert_called_once()
