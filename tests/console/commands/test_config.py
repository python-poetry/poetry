import json
import os

import pytest

from cleo.testers import CommandTester

from poetry.config.config_source import ConfigSource
from poetry.factory import Factory


def test_list_displays_default_value_if_not_set(app, config):
    command = app.find("config")
    tester = CommandTester(command)
    tester.execute("--list")

    expected = """cache-dir = "/foo"
virtualenvs.create = true
virtualenvs.in-project = false
virtualenvs.path = {path}  # /foo{sep}virtualenvs
""".format(
        path=json.dumps(os.path.join("{cache-dir}", "virtualenvs")), sep=os.path.sep
    )

    assert expected == tester.io.fetch_output()


def test_list_displays_set_get_setting(app, config):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("virtualenvs.create false")

    tester.execute("--list")

    expected = """cache-dir = "/foo"
virtualenvs.create = false
virtualenvs.in-project = false
virtualenvs.path = {path}  # /foo{sep}virtualenvs
""".format(
        path=json.dumps(os.path.join("{cache-dir}", "virtualenvs")), sep=os.path.sep
    )

    assert 0 == config.set_config_source.call_count
    assert expected == tester.io.fetch_output()


def test_display_single_setting(app, config):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("virtualenvs.create")

    expected = """true
"""

    assert expected == tester.io.fetch_output()


def test_display_single_local_setting(app, config, fixture_dir):
    poetry = Factory().create_poetry(fixture_dir("with_local_config"))
    app._poetry = poetry

    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("virtualenvs.create")

    expected = """false
"""

    assert expected == tester.io.fetch_output()


def test_list_displays_set_get_local_setting(app, config):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("virtualenvs.create false --local")

    tester.execute("--list")

    expected = """cache-dir = "/foo"
virtualenvs.create = false
virtualenvs.in-project = false
virtualenvs.path = {path}  # /foo{sep}virtualenvs
""".format(
        path=json.dumps(os.path.join("{cache-dir}", "virtualenvs")), sep=os.path.sep
    )

    assert 1 == config.set_config_source.call_count
    assert expected == tester.io.fetch_output()


def test_set_pypi_token(app, auth_config_source):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("pypi-token.pypi mytoken")

    tester.execute("--list")

    assert "mytoken" == auth_config_source.config["pypi-token"]["pypi"]


def test_set_client_cert(app, auth_config_source, mocker):
    mocker.spy(ConfigSource, "__init__")
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("certificates.foo.client-cert path/to/cert.pem")

    assert (
        "path/to/cert.pem"
        == auth_config_source.config["certificates"]["foo"]["client-cert"]
    )


def test_set_cert(app, auth_config_source):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("certificates.foo.cert path/to/ca.pem")

    assert "path/to/ca.pem" == auth_config_source.config["certificates"]["foo"]["cert"]


def test_set_repository(app, config_source):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("repositories.foo https://foo.bar/simple/")

    assert (
        "https://foo.bar/simple/" == config_source.config["repositories"]["foo"]["url"]
    )
    assert "foo" == config_source.config["repositories"]["foo"]["name"]

    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["default"]
    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["secondary"]


def test_set_repository_with_repos(app, config_source):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("repos.foo https://foo.bar/simple/")

    assert (
        "https://foo.bar/simple/" == config_source.config["repositories"]["foo"]["url"]
    )
    assert "foo" == config_source.config["repositories"]["foo"]["name"]

    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["default"]
    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["secondary"]


def test_set_repository_as_default(app, config_source):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("repositories.foo https://foo.bar/simple/")
    tester.execute("repositories.foo.default true")

    assert (
        "https://foo.bar/simple/" == config_source.config["repositories"]["foo"]["url"]
    )
    assert "foo" == config_source.config["repositories"]["foo"]["name"]
    assert "true" == config_source.config["repositories"]["foo"]["default"]

    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["secondary"]


def test_set_repository_as_secondary(app, config_source):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("repositories.foo https://foo.bar/simple/")
    tester.execute("repositories.foo.secondary true")

    assert (
        "https://foo.bar/simple/" == config_source.config["repositories"]["foo"]["url"]
    )
    assert "foo" == config_source.config["repositories"]["foo"]["name"]
    assert "true" == config_source.config["repositories"]["foo"]["secondary"]

    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["default"]


def test_set_repository_as_default_and_secondary(app, config_source):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("repositories.foo https://foo.bar/simple/")

    # first set repository as default
    tester.execute("repositories.foo.default true")

    assert (
        "https://foo.bar/simple/" == config_source.config["repositories"]["foo"]["url"]
    )
    assert "foo" == config_source.config["repositories"]["foo"]["name"]
    assert "true" == config_source.config["repositories"]["foo"]["default"]

    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["secondary"]

    # now set repository as secondary
    tester.execute("repositories.foo.secondary true")

    assert "true" == config_source.config["repositories"]["foo"]["secondary"]

    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["default"]


def test_set_repository_as_secondary_and_default(app, config_source):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("repositories.foo https://foo.bar/simple/")

    # first set repository as secondary
    tester.execute("repositories.foo.secondary true")

    assert (
        "https://foo.bar/simple/" == config_source.config["repositories"]["foo"]["url"]
    )
    assert "foo" == config_source.config["repositories"]["foo"]["name"]
    assert "true" == config_source.config["repositories"]["foo"]["secondary"]

    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["default"]

    # now set repository as default
    tester.execute("repositories.foo.default true")

    assert "true" == config_source.config["repositories"]["foo"]["default"]

    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["secondary"]


def test_unset_repository_name(app):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("repositories.foo https://foo.bar/simple/")

    with pytest.raises(ValueError) as excinfo:
        tester.execute("repositories.foo.name --unset")

    assert "Repository can't exist without name or url." in str(excinfo.value)


def test_unset_repository_url(app):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("repositories.foo https://foo.bar/simple/")

    with pytest.raises(ValueError) as excinfo:
        tester.execute("repositories.foo.url --unset")

    assert "Repository can't exist without name or url." in str(excinfo.value)


def test_unset_repository_as_default(app, config_source):
    command = app.find("config")
    tester = CommandTester(command)

    # first create repository and set repository as default
    tester.execute("repositories.foo https://foo.bar/simple/")
    tester.execute("repositories.foo.default true")

    assert (
        "https://foo.bar/simple/" == config_source.config["repositories"]["foo"]["url"]
    )
    assert "foo" == config_source.config["repositories"]["foo"]["name"]
    assert "true" == config_source.config["repositories"]["foo"]["default"]

    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["secondary"]

    # now unset default flag
    tester.execute("repositories.foo.default --unset")

    assert (
        "https://foo.bar/simple/" == config_source.config["repositories"]["foo"]["url"]
    )
    assert "foo" == config_source.config["repositories"]["foo"]["name"]
    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["default"]
    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["secondary"]


def test_unset_repository_as_secondary(app, config_source):
    command = app.find("config")
    tester = CommandTester(command)

    # first create repository and set repository as default
    tester.execute("repositories.foo https://foo.bar/simple/")
    tester.execute("repositories.foo.secondary true")

    assert (
        "https://foo.bar/simple/" == config_source.config["repositories"]["foo"]["url"]
    )
    assert "foo" == config_source.config["repositories"]["foo"]["name"]
    assert "true" == config_source.config["repositories"]["foo"]["secondary"]

    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["default"]

    # now unset secondary flag
    tester.execute("repositories.foo.secondary --unset")

    assert (
        "https://foo.bar/simple/" == config_source.config["repositories"]["foo"]["url"]
    )
    assert "foo" == config_source.config["repositories"]["foo"]["name"]
    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["default"]
    with pytest.raises(KeyError):
        _ = config_source.config["repositories"]["foo"]["secondary"]
