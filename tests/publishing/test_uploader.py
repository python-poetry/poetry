from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cleo.io.null_io import NullIO

from poetry.factory import Factory
from poetry.publishing.uploader import Uploader
from poetry.publishing.uploader import UploadError


if TYPE_CHECKING:
    import responses

    from pytest_mock import MockerFixture

    from tests.types import FixtureDirGetter


@pytest.fixture
def uploader(fixture_dir: FixtureDirGetter) -> Uploader:
    return Uploader(Factory().create_poetry(fixture_dir("simple_project")), NullIO())


def test_uploader_properly_handles_400_errors(
    http: responses.RequestsMock, uploader: Uploader
) -> None:
    http.post("https://foo.com", status=400, body="Bad request")

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert str(e.value) == "HTTP Error 400: Bad Request | b'Bad request'"


def test_uploader_properly_handles_403_errors(
    http: responses.RequestsMock, uploader: Uploader
) -> None:
    http.post("https://foo.com", status=403, body="Unauthorized")

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert str(e.value) == "HTTP Error 403: Forbidden | b'Unauthorized'"


def test_uploader_properly_handles_nonstandard_errors(
    http: responses.RequestsMock, uploader: Uploader
) -> None:
    # content based off a true story.
    # Message changed to protect the ~~innocent~~ guilty.
    content = (
        b'{\n "errors": [ {\n '
        b'"status": 400,'
        b'"message": "I cant let you do that, dave"\n'
        b"} ]\n}"
    )
    http.post("https://foo.com", status=400, body=content)

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert str(e.value) == f"HTTP Error 400: Bad Request | {content!r}"


@pytest.mark.parametrize(
    ("status", "code"),
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
    http: responses.RequestsMock, uploader: Uploader, status: int, code: str
) -> None:
    http.post("https://foo.com", status=status)

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert (
        str(e.value)
        == "Redirects are not supported. Is the URL missing a trailing slash?"
    )


def test_uploader_properly_handles_301_redirects(
    http: responses.RequestsMock, uploader: Uploader
) -> None:
    http.post("https://foo.com", status=301, body="Redirect")

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert (
        str(e.value)
        == "Redirects are not supported. Is the URL missing a trailing slash?"
    )


def test_uploader_registers_for_appropriate_400_errors(
    mocker: MockerFixture, http: responses.RequestsMock, uploader: Uploader
) -> None:
    register = mocker.patch("poetry.publishing.uploader.Uploader._register")
    http.post("https://foo.com", status=400, body="No package was ever registered")

    with pytest.raises(UploadError):
        uploader.upload("https://foo.com")

    assert register.call_count == 1


@pytest.mark.parametrize(
    "status, body",
    [
        (409, ""),
        (400, "File already exists"),
        (400, "Repository does not allow updating assets"),
        (400, "cannot be updated"),
        (403, "Not enough permissions to overwrite artifact"),
        (400, "file name has already been taken"),
    ],
)
def test_uploader_skips_existing(
    http: responses.RequestsMock, uploader: Uploader, status: int, body: str
) -> None:
    http.post("https://foo.com", status=status, body=body)

    # should not raise
    uploader.upload("https://foo.com", skip_existing=True)


def test_uploader_skip_existing_bubbles_unskippable_errors(
    http: responses.RequestsMock, uploader: Uploader
) -> None:
    http.post("https://foo.com", status=403, body="Unauthorized")

    with pytest.raises(UploadError):
        uploader.upload("https://foo.com", skip_existing=True)


def test_uploader_properly_handles_file_not_existing(
    mocker: MockerFixture, http: responses.RequestsMock, uploader: Uploader
) -> None:
    mocker.patch("pathlib.Path.is_file", return_value=False)

    with pytest.raises(UploadError) as e:
        uploader.upload("https://foo.com")

    assert f"Archive ({uploader.files[0]}) does not exist" == str(e.value)


def test_uploader_post_data_wheel(fixture_dir: FixtureDirGetter) -> None:
    file = (
        fixture_dir("simple_project")
        / "dist"
        / "simple_project-1.2.3-py2.py3-none-any.whl"
    )
    assert Uploader.post_data(file) == {
        "md5_digest": "fb4a5266406b9cf34ceaa88d1c8b7a01",
        "sha256_digest": "fc365a242d4de8b8661babc088f44b3df25e9e0017ef5dd7140dfe50f9323e16",
        "blake2_256_digest": "2e006d1fbfef0ed38fbded1ec1614dc4fd66f81061fe290528e2744dbc25ce31",
        "filetype": "bdist_wheel",
        "pyversion": "py2.py3",
        "metadata_version": "2.1",
        "name": "simple-project",
        "version": "1.2.3",
        "summary": "Some description.",
        "author": "Sébastien Eustace",
        "author_email": "sebastien@eustace.io",
        "license": "MIT",
        "classifiers": [
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Topic :: Software Development :: Build Tools",
            "Topic :: Software Development :: Libraries :: Python Modules",
        ],
        "requires_python": ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*",
        "description": "My Package\n==========\n\n",
        "description_content_type": "text/x-rst",
        "keywords": "packaging, dependency, poetry",
        "home_page": "https://poetry.eustace.io",
        "project_urls": [
            "Documentation, https://poetry.eustace.io/docs",
            "Repository, https://github.com/sdispater/poetry",
        ],
    }


def test_uploader_post_data_sdist(fixture_dir: FixtureDirGetter) -> None:
    file = fixture_dir("simple_project") / "dist" / "simple_project-1.2.3.tar.gz"
    assert Uploader.post_data(file) == {
        "md5_digest": "e611cbb8f31258243d90f7681dfda68a",
        "sha256_digest": "c4a72becabca29ec2a64bf8c820bbe204d2268f53e102501ea5605bc1c1675d1",
        "blake2_256_digest": "d3df22f4944f6acd02105e7e2df61ef63c7b0f4337a12df549ebc2805a13c2be",
        "filetype": "sdist",
        "pyversion": "source",
        "metadata_version": "2.1",
        "name": "simple-project",
        "version": "1.2.3",
        "summary": "Some description.",
        "author": "Sébastien Eustace",
        "author_email": "sebastien@eustace.io",
        "classifiers": [
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Topic :: Software Development :: Build Tools",
            "Topic :: Software Development :: Libraries :: Python Modules",
        ],
        "requires_python": ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*",
        "keywords": "packaging, dependency, poetry",
        "home_page": "https://poetry.eustace.io",
        "project_urls": [
            "Documentation, https://poetry.eustace.io/docs",
            "Repository, https://github.com/sdispater/poetry",
        ],
    }
