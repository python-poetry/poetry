import json
import os

from cleo.testers import CommandTester

from poetry.config.config_source import ConfigSource
from poetry.factory import Factory


def test_list_displays_default_value_if_not_set(app, config):
    command = app.find("config")
    tester = CommandTester(command)
    tester.execute("--list")

    expected = """cache-dir = "/foo"
experimental.new-installer = true
virtualenvs.create = true
virtualenvs.in-project = false
virtualenvs.in-project-dir = ".venv"
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
experimental.new-installer = true
virtualenvs.create = false
virtualenvs.in-project = false
virtualenvs.in-project-dir = ".venv"
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
experimental.new-installer = true
virtualenvs.create = false
virtualenvs.in-project = false
virtualenvs.in-project-dir = ".venv"
virtualenvs.path = {path}  # /foo{sep}virtualenvs
""".format(
        path=json.dumps(os.path.join("{cache-dir}", "virtualenvs")), sep=os.path.sep
    )

    assert 1 == config.set_config_source.call_count
    assert expected == tester.io.fetch_output()


def test_set_pypi_token(app, config, config_source, auth_config_source):
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("pypi-token.pypi mytoken")

    tester.execute("--list")

    assert "mytoken" == auth_config_source.config["pypi-token"]["pypi"]


def test_set_client_cert(app, config_source, auth_config_source, mocker):
    mocker.spy(ConfigSource, "__init__")
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("certificates.foo.client-cert path/to/cert.pem")

    assert (
        "path/to/cert.pem"
        == auth_config_source.config["certificates"]["foo"]["client-cert"]
    )


def test_set_cert(app, config_source, auth_config_source, mocker):
    mocker.spy(ConfigSource, "__init__")
    command = app.find("config")
    tester = CommandTester(command)

    tester.execute("certificates.foo.cert path/to/ca.pem")

    assert "path/to/ca.pem" == auth_config_source.config["certificates"]["foo"]["cert"]
