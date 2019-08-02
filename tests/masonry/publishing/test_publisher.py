import pytest

from poetry.io.null_io import NullIO
from poetry.masonry.publishing.publisher import Publisher
from poetry.poetry import Poetry


def test_publish_publishes_to_pypi_by_default(fixture_dir, mocker):
    uploader_auth = mocker.patch("poetry.masonry.publishing.uploader.Uploader.auth")
    uploader_upload = mocker.patch("poetry.masonry.publishing.uploader.Uploader.upload")
    poetry = Poetry.create(fixture_dir("sample_project"))
    poetry.config.merge(
        {"http-basic": {"pypi": {"username": "foo", "password": "bar"}}}
    )
    publisher = Publisher(poetry, NullIO())

    publisher.publish(None, None, None)

    assert [("foo", "bar")] == uploader_auth.call_args
    assert [("https://upload.pypi.org/legacy/",)] == uploader_upload.call_args


def test_publish_can_publish_to_given_repository(fixture_dir, mocker):
    uploader_auth = mocker.patch("poetry.masonry.publishing.uploader.Uploader.auth")
    uploader_upload = mocker.patch("poetry.masonry.publishing.uploader.Uploader.upload")
    poetry = Poetry.create(fixture_dir("sample_project"))
    poetry.config.merge(
        {
            "repositories": {"my-repo": {"url": "http://foo.bar"}},
            "http-basic": {"my-repo": {"username": "foo", "password": "bar"}},
        }
    )
    publisher = Publisher(poetry, NullIO())

    publisher.publish("my-repo", None, None)

    assert [("foo", "bar")] == uploader_auth.call_args
    assert [("http://foo.bar",)] == uploader_upload.call_args


def test_publish_raises_error_for_undefined_repository(fixture_dir, mocker):
    poetry = Poetry.create(fixture_dir("sample_project"))
    poetry.config.merge(
        {"http-basic": {"my-repo": {"username": "foo", "password": "bar"}}}
    )
    publisher = Publisher(poetry, NullIO())

    with pytest.raises(RuntimeError):
        publisher.publish("my-repo", None, None)
