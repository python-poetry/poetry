import json
import os

import pytest

from poetry.config.config_source import ConfigSource
from poetry.core.pyproject.exceptions import PyProjectException
from poetry.factory import Factory


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("config")


def test_show_config_with_local_config_file_empty(tester, mocker):
    mocker.patch(
        "poetry.factory.Factory.create_poetry",
        side_effect=PyProjectException("[tool.poetry] section not found"),
    )
    tester.execute()

    assert "" == tester.io.fetch_output()


def test_list_displays_default_value_if_not_set(tester, config, config_cache_dir):
    tester.execute("--list")

    expected = """cache-dir = {cache}
experimental.new-installer = true
installer.parallel = true
virtualenvs.create = true
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {path}  # {virtualenvs}
""".format(
        cache=json.dumps(str(config_cache_dir)),
        path=json.dumps(os.path.join("{cache-dir}", "virtualenvs")),
        virtualenvs=str(config_cache_dir / "virtualenvs"),
    )

    assert expected == tester.io.fetch_output()


def test_list_displays_set_get_setting(tester, config, config_cache_dir):
    tester.execute("virtualenvs.create false")

    tester.execute("--list")

    expected = """cache-dir = {cache}
experimental.new-installer = true
installer.parallel = true
virtualenvs.create = false
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {path}  # {virtualenvs}
""".format(
        cache=json.dumps(str(config_cache_dir)),
        path=json.dumps(os.path.join("{cache-dir}", "virtualenvs")),
        virtualenvs=str(config_cache_dir / "virtualenvs"),
    )

    assert 0 == config.set_config_source.call_count
    assert expected == tester.io.fetch_output()


def test_display_single_setting(tester, config):
    tester.execute("virtualenvs.create")

    expected = """true
"""

    assert expected == tester.io.fetch_output()


def test_display_single_local_setting(command_tester_factory, fixture_dir):
    tester = command_tester_factory(
        "config", poetry=Factory().create_poetry(fixture_dir("with_local_config"))
    )
    tester.execute("virtualenvs.create")

    expected = """false
"""

    assert expected == tester.io.fetch_output()


def test_list_displays_set_get_local_setting(tester, config, config_cache_dir):
    tester.execute("virtualenvs.create false --local")

    tester.execute("--list")

    expected = """cache-dir = {cache}
experimental.new-installer = true
installer.parallel = true
virtualenvs.create = false
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {path}  # {virtualenvs}
""".format(
        cache=json.dumps(str(config_cache_dir)),
        path=json.dumps(os.path.join("{cache-dir}", "virtualenvs")),
        virtualenvs=str(config_cache_dir / "virtualenvs"),
    )

    assert 1 == config.set_config_source.call_count
    assert expected == tester.io.fetch_output()


def test_set_pypi_token(tester, auth_config_source):
    tester.execute("pypi-token.pypi mytoken")
    tester.execute("--list")

    assert "mytoken" == auth_config_source.config["pypi-token"]["pypi"]


def test_set_client_cert(tester, auth_config_source, mocker):
    mocker.spy(ConfigSource, "__init__")

    tester.execute("certificates.foo.client-cert path/to/cert.pem")

    assert (
        "path/to/cert.pem"
        == auth_config_source.config["certificates"]["foo"]["client-cert"]
    )


def test_set_cert(tester, auth_config_source, mocker):
    mocker.spy(ConfigSource, "__init__")

    tester.execute("certificates.foo.cert path/to/ca.pem")

    assert "path/to/ca.pem" == auth_config_source.config["certificates"]["foo"]["cert"]


def test_config_installer_parallel(tester, command_tester_factory):
    tester.execute("--local installer.parallel")
    assert tester.io.fetch_output().strip() == "true"

    workers = command_tester_factory(
        "install"
    )._command._installer._executor._max_workers
    assert workers > 1

    tester.io.clear_output()
    tester.execute("--local installer.parallel false")
    tester.execute("--local installer.parallel")
    assert tester.io.fetch_output().strip() == "false"

    workers = command_tester_factory(
        "install"
    )._command._installer._executor._max_workers
    assert workers == 1
