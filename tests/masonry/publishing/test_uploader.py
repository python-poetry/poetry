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


def test_uploader_properly_handles_400_errors(http):
    http.register_uri(http.POST, "https://foo.com", status=400, body="Bad request")
    uploader = Uploader(Poetry.create(project("complete")), NullIO())

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert "HTTP Error 400: Bad Request" == str(e.value)


def test_uploader_properly_handles_403_errors(http):
    http.register_uri(http.POST, "https://foo.com", status=403, body="Unauthorized")
    uploader = Uploader(Poetry.create(project("complete")), NullIO())

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert "HTTP Error 403: Forbidden" == str(e.value)


def test_uploader_registers_for_appropriate_400_errors(mocker, http):
    register = mocker.patch("poetry.masonry.publishing.uploader.Uploader._register")
    http.register_uri(
        http.POST, "https://foo.com", status=400, body="No package was ever registered"
    )
    uploader = Uploader(Poetry.create(project("complete")), NullIO())

    with pytest.raises(UploadError):
        uploader.upload("https://foo.com")

    assert 1 == register.call_count
