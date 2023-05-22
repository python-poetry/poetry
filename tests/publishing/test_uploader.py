from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cleo.io.null_io import NullIO

from poetry.factory import Factory
from poetry.publishing.uploader import Uploader
from poetry.publishing.uploader import UploadError


if TYPE_CHECKING:
    import httpretty

    from pytest_mock import MockerFixture

    from tests.types import FixtureDirGetter


@pytest.fixture
def uploader(fixture_dir: FixtureDirGetter) -> Uploader:
    return Uploader(Factory().create_poetry(fixture_dir("simple_project")), NullIO())


def test_uploader_properly_handles_400_errors(
    http: type[httpretty.httpretty], uploader: Uploader
) -> None:
    http.register_uri(http.POST, "https://foo.com", status=400, body="Bad request")

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert str(e.value) == "HTTP Error 400: Bad Request | b'Bad request'"


def test_uploader_properly_handles_403_errors(
    http: type[httpretty.httpretty], uploader: Uploader
) -> None:
    http.register_uri(http.POST, "https://foo.com", status=403, body="Unauthorized")

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert str(e.value) == "HTTP Error 403: Forbidden | b'Unauthorized'"


def test_uploader_properly_handles_nonstandard_errors(
    http: type[httpretty.httpretty], uploader: Uploader
) -> None:
    # content based off a true story.
    # Message changed to protect the ~~innocent~~ guilty.
    content = (
        b'{\n "errors": [ {\n '
        b'"status": 400,'
        b'"message": "I cant let you do that, dave"\n'
        b"} ]\n}"
    )
    http.register_uri(http.POST, "https://foo.com", status=400, body=content)

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert str(e.value) == f"HTTP Error 400: Bad Request | {content!r}"


@pytest.mark.parametrize(
    "status, body",
    [
        (308, "Permanent Redirect"),
        (307, "Temporary Redirect"),
        (304, "Not Modified"),
        (303, "See Other"),
        (302, "Found"),
        (301, "Moved Permanently"),
        (300, "Multiple Choices"),
    ],
)
def test_uploader_properly_handles_redirects(
    http: type[httpretty.httpretty], uploader: Uploader, status: int, body: str
) -> None:
    http.register_uri(http.POST, "https://foo.com", status=status, body=body)

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert (
        str(e.value)
        == "Redirects are not supported. Is the URL missing a trailing slash?"
    )


def test_uploader_properly_handles_301_redirects(
    http: type[httpretty.httpretty], uploader: Uploader
) -> None:
    http.register_uri(http.POST, "https://foo.com", status=301, body="Redirect")

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert (
        str(e.value)
        == "Redirects are not supported. Is the URL missing a trailing slash?"
    )


def test_uploader_registers_for_appropriate_400_errors(
    mocker: MockerFixture, http: type[httpretty.httpretty], uploader: Uploader
) -> None:
    register = mocker.patch("poetry.publishing.uploader.Uploader._register")
    http.register_uri(
        http.POST, "https://foo.com", status=400, body="No package was ever registered"
    )

    with pytest.raises(UploadError):
        uploader.upload("https://foo.com")

    assert register.call_count == 1


@pytest.mark.parametrize(
    "status, body",
    [
        (409, ""),
        (400, "File already exists"),
        (400, "Repository does not allow updating assets"),
        (403, "Not enough permissions to overwrite artifact"),
        (400, "file name has already been taken"),
    ],
)
def test_uploader_skips_existing(
    http: type[httpretty.httpretty], uploader: Uploader, status: int, body: str
) -> None:
    http.register_uri(http.POST, "https://foo.com", status=status, body=body)

    # should not raise
    uploader.upload("https://foo.com", skip_existing=True)


def test_uploader_skip_existing_bubbles_unskippable_errors(
    http: type[httpretty.httpretty], uploader: Uploader
) -> None:
    http.register_uri(http.POST, "https://foo.com", status=403, body="Unauthorized")

    with pytest.raises(UploadError):
        uploader.upload("https://foo.com", skip_existing=True)


def test_uploader_properly_handles_file_not_existing(
    mocker: MockerFixture, http: type[httpretty.httpretty], uploader: Uploader
) -> None:
    mocker.patch("pathlib.Path.is_file", return_value=False)

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert f"Archive ({uploader.files[0]}) does not exist" == str(e.value)
