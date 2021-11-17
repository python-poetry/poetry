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


def test_unset_pypi_token(tester, auth_config_source):
    tester.execute("pypi-token.pypi mytoken")
    tester.execute("--unset pypi-token.pypi")

    assert "pypi" not in auth_config_source.config["pypi-token"]


def test_set_pypi_token_multiple_error(tester):
    with pytest.raises(ValueError) as err:
        tester.execute("pypi-token.pypi mytoken other")

    assert "Expected only one argument (token), got 2" == str(err.value)


def test_set_http_basic(tester, auth_config_source):
    tester.execute("http-basic.pypi my_username my_password")
    expected_credentials = {"username": "my_username", "password": "my_password"}
    assert expected_credentials == auth_config_source.config["http-basic"]["pypi"]


def test_unset_http_basic(tester, auth_config_source):
    tester.execute("http-basic.pypi my_username my_password")
    tester.execute("--unset http-basic.pypi")

    assert "pypi" not in auth_config_source.config["http-basic"]


def test_set_http_basic_multiple_error(tester):
    with pytest.raises(ValueError) as err:
        tester.execute("http-basic.pypi my_username my_password other")

    assert "Expected one or two arguments (username, password), got 3" == str(err.value)


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


def test_unset_cert(tester, auth_config_source, mocker):
    mocker.spy(ConfigSource, "__init__")

    tester.execute("certificates.foo.cert path/to/ca.pem")
    tester.execute("--unset certificates.foo.cert")

    assert "cert" not in auth_config_source.config["certificates"]["foo"]


def test_set_cert_multiple_error(tester, auth_config_source, mocker):
    mocker.spy(ConfigSource, "__init__")

    with pytest.raises(ValueError) as err:
        tester.execute("certificates.foo.cert path/to/ca.pem other")

    assert "You must pass exactly 1 value" == str(err.value)


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


def test_cannot_set_and_unset_simultaneously(tester):
    with pytest.raises(RuntimeError) as err:
        tester.execute("--unset foo bar")

    assert "You can not combine a setting value with --unset" == str(err.value)


def test_cannot_get_missing_setting(tester):
    with pytest.raises(ValueError) as err:
        tester.execute("missing_config_value")

    assert "There is no missing_config_value setting." == str(err.value)


def test_config_add_repo(tester, config):
    tester.execute("repositories.foo https://bar.com")

    assert "foo" in config.config_source.config["repositories"]
    assert (
        "https://bar.com" == config.config_source.config["repositories"]["foo"]["url"]
    )


def test_config_get_repo(tester):
    tester.execute("repositories.foo https://bar.com")
    tester.execute("repositories.foo.url")

    expected = """https://bar.com
"""

    assert expected == tester.io.fetch_output()


def test_config_get_repo_multiple(tester):
    tester.execute("repositories.foo https://bar.com")
    tester.execute("repositories.baz https://qux.com")
    tester.execute("repositories")

    expected = """{'foo': {'url': 'https://bar.com'}, 'baz': {'url': 'https://qux.com'}}
"""

    assert expected == tester.io.fetch_output()


def test_config_remove_repo(tester, config):
    tester.execute("repositories.foo https://bar.com")
    tester.execute("--unset repositories.foo")

    assert {} == config.config_source.config["repositories"]


def test_config_cannot_add_repo_with_multiple_urls(tester):
    with pytest.raises(ValueError) as err:
        tester.execute("repositories.foo https://bar.com https://baz.com")

    assert (
        "You must pass the url. Example: poetry config repositories.foo https://bar.com"
        == str(err.value)
    )


def test_config_repos_cannot_remove_entire_section(tester):
    with pytest.raises(ValueError) as err:
        tester.execute("repo https://bar.com")

    assert "You cannot remove the [repositories] section" == str(err.value)


def test_config_repos_cannot_get_undefined(tester):
    with pytest.raises(ValueError) as err:
        tester.execute("repositories.missing_repo")

    assert "There is no missing_repo repository defined" == str(err.value)


def test_config_repos_cannot_unset_missing(tester):
    with pytest.raises(ValueError) as err:
        tester.execute("--unset repo.missing_repo")

    assert "There is no missing_repo repository defined" == str(err.value)


def test_list_repos(tester, config, config_cache_dir):
    tester.execute("repositories.foo https://bar.com")
    tester.execute("--list")

    expected = """cache-dir = {cache}
experimental.new-installer = true
installer.parallel = true
repositories.foo.url = "https://bar.com"
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
