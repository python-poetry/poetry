import pytest

from poetry.factory import Factory
from poetry.io.null_io import NullIO
from poetry.publishing.uploader import Uploader
from poetry.publishing.uploader import UploadError


def test_uploader_properly_handles_400_errors(http, fixture_dir):
    http.register_uri(http.POST, "https://foo.com", status=400, body="Bad request")
    uploader = Uploader(
        Factory().create_poetry(fixture_dir("simple_project")), NullIO()
    )

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert "HTTP Error 400: Bad Request" == str(e.value)


def test_uploader_properly_handles_403_errors(http, fixture_dir):
    http.register_uri(http.POST, "https://foo.com", status=403, body="Unauthorized")
    uploader = Uploader(
        Factory().create_poetry(fixture_dir("simple_project")), NullIO()
    )

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert "HTTP Error 403: Forbidden" == str(e.value)


def test_uploader_properly_handles_301_redirects(http, fixture_dir):
    http.register_uri(http.POST, "https://foo.com", status=301, body="Redirect")
    uploader = Uploader(
        Factory().create_poetry(fixture_dir("simple_project")), NullIO()
    )

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert "Redirects are not supported. Is the URL missing a trailing slash?" == str(
        e.value
    )


def test_uploader_registers_for_appropriate_400_errors(mocker, http, fixture_dir):
    register = mocker.patch("poetry.publishing.uploader.Uploader._register")
    http.register_uri(
        http.POST, "https://foo.com", status=400, body="No package was ever registered"
    )
    uploader = Uploader(
        Factory().create_poetry(fixture_dir("simple_project")), NullIO()
    )

    with pytest.raises(UploadError):
        uploader.upload("https://foo.com")

    assert 1 == register.call_count
