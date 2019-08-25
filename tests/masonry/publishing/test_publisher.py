import pytest

from poetry.io.null_io import NullIO
from poetry.masonry.publishing.publisher import Publisher
from poetry.poetry import Poetry
from poetry.utils._compat import Path


def test_publish_publishes_to_pypi_by_default(fixture_dir, mocker, config):
    uploader_auth = mocker.patch("poetry.masonry.publishing.uploader.Uploader.auth")
    uploader_upload = mocker.patch("poetry.masonry.publishing.uploader.Uploader.upload")
    poetry = Poetry.create(fixture_dir("sample_project"))
    poetry._config = config
    poetry.config.merge(
        {"http-basic": {"pypi": {"username": "foo", "password": "bar"}}}
    )
    publisher = Publisher(poetry, NullIO())

    publisher.publish(None, None, None)

    assert [("foo", "bar")] == uploader_auth.call_args
    assert [
        ("https://upload.pypi.org/legacy/",),
        {"custom_ca": None, "client_cert": None},
    ] == uploader_upload.call_args


def test_publish_can_publish_to_given_repository(fixture_dir, mocker, config):
    uploader_auth = mocker.patch("poetry.masonry.publishing.uploader.Uploader.auth")
    uploader_upload = mocker.patch("poetry.masonry.publishing.uploader.Uploader.upload")
    poetry = Poetry.create(fixture_dir("sample_project"))
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
    assert [
        ("http://foo.bar",),
        {"custom_ca": None, "client_cert": None},
    ] == uploader_upload.call_args


def test_publish_raises_error_for_undefined_repository(fixture_dir, mocker, config):
    poetry = Poetry.create(fixture_dir("sample_project"))
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
    poetry = Poetry.create(fixture_dir("sample_project"))
    poetry._config = config
    poetry.config.merge({"pypi-token": {"pypi": "my-token"}})
    publisher = Publisher(poetry, NullIO())

    publisher.publish(None, None, None)

    assert [("__token__", "my-token")] == uploader_auth.call_args
    assert [
        ("https://upload.pypi.org/legacy/",),
        {"custom_ca": None, "client_cert": None},
    ] == uploader_upload.call_args


def test_publish_uses_custom_ca(fixture_dir, mocker, config):
    custom_ca = "path/to/ca.pem"
    uploader_auth = mocker.patch("poetry.masonry.publishing.uploader.Uploader.auth")
    uploader_upload = mocker.patch("poetry.masonry.publishing.uploader.Uploader.upload")
    poetry = Poetry.create(fixture_dir("sample_project"))
    poetry._config = config
    # Adding the empty string for username/password is a bit of a hack but otherwise it will prompt for them
    # username and password are optional but there is no good way of specifying a lack of them other than empty string
    poetry.config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar"}},
            "http-basic": {"foo": {"username": "", "password": ""}},
            "certificates": {"foo": {"custom-ca": custom_ca}},
        }
    )
    publisher = Publisher(poetry, NullIO())

    publisher.publish("foo", None, None)

    assert [("", "")] == uploader_auth.call_args
    assert [
        ("https://foo.bar",),
        {"custom_ca": Path(custom_ca), "client_cert": None},
    ] == uploader_upload.call_args


def test_publish_uses_client_cert(fixture_dir, mocker, config):
    client_cert = "path/to/client.pem"
    uploader_auth = mocker.patch("poetry.masonry.publishing.uploader.Uploader.auth")
    uploader_upload = mocker.patch("poetry.masonry.publishing.uploader.Uploader.upload")
    poetry = Poetry.create(fixture_dir("sample_project"))
    poetry._config = config
    # Adding the empty string for username/password is a bit of a hack but otherwise it will prompt for them
    # username and password are optional but there is no good way of specifying a lack of them other than empty string
    poetry.config.merge(
        {
            "repositories": {"foo": {"url": "https://foo.bar"}},
            "http-basic": {"foo": {"username": "", "password": ""}},
            "certificates": {"foo": {"client-cert": client_cert}},
        }
    )
    publisher = Publisher(poetry, NullIO())

    publisher.publish("foo", None, None)

    assert [("", "")] == uploader_auth.call_args
    assert [
        ("https://foo.bar",),
        {"custom_ca": None, "client_cert": Path(client_cert)},
    ] == uploader_upload.call_args
