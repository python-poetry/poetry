import pytest

from poetry.factory import Factory
from poetry.io.null_io import NullIO
from poetry.masonry.publishing.publisher import Publisher


def test_publish_publishes_to_pypi_by_default(fixture_dir, mocker, config):
    uploader_auth = mocker.patch("poetry.masonry.publishing.uploader.Uploader.auth")
    uploader_upload = mocker.patch("poetry.masonry.publishing.uploader.Uploader.upload")
    poetry = Factory().create_poetry(fixture_dir("sample_project"))
    poetry._config = config
    poetry.config.merge(
        {"http-basic": {"pypi": {"username": "foo", "password": "bar"}}}
    )
    publisher = Publisher(poetry, NullIO())

    publisher.publish(None, None, None)

    assert [("foo", "bar")] == uploader_auth.call_args
    assert [("https://upload.pypi.org/legacy/",)] == uploader_upload.call_args


def test_publish_can_publish_to_given_repository(fixture_dir, mocker, config):
    uploader_auth = mocker.patch("poetry.masonry.publishing.uploader.Uploader.auth")
    uploader_upload = mocker.patch("poetry.masonry.publishing.uploader.Uploader.upload")
    poetry = Factory().create_poetry(fixture_dir("sample_project"))
    poetry._config = config
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


def test_publish_raises_error_for_undefined_repository(fixture_dir, mocker, config):
    poetry = Factory().create_poetry(fixture_dir("sample_project"))
    poetry._config = config
    poetry.config.merge(
        {"http-basic": {"my-repo": {"username": "foo", "password": "bar"}}}
    )
    publisher = Publisher(poetry, NullIO())

    with pytest.raises(RuntimeError):
        publisher.publish("my-repo", None, None)


def test_publish_uses_token_if_it_exists(fixture_dir, mocker, config):
    uploader_auth = mocker.patch("poetry.masonry.publishing.uploader.Uploader.auth")
    uploader_upload = mocker.patch("poetry.masonry.publishing.uploader.Uploader.upload")
    poetry = Factory().create_poetry(fixture_dir("sample_project"))
    poetry._config = config
    poetry.config.merge({"pypi-token": {"pypi": "my-token"}})
    publisher = Publisher(poetry, NullIO())

    publisher.publish(None, None, None)

    assert [("__token__", "my-token")] == uploader_auth.call_args
    assert [("https://upload.pypi.org/legacy/",)] == uploader_upload.call_args
