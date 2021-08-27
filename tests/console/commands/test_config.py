import json
import os

<<<<<<< HEAD
from typing import TYPE_CHECKING

import pytest

from poetry.core.pyproject.exceptions import PyProjectException

from poetry.config.config_source import ConfigSource
from poetry.factory import Factory


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.config.dict_config_source import DictConfigSource
    from tests.conftest import Config
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter


@pytest.fixture()
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
    return command_tester_factory("config")


def test_show_config_with_local_config_file_empty(
    tester: "CommandTester", mocker: "MockerFixture"
):
=======
import pytest

from poetry.config.config_source import ConfigSource
from poetry.core.pyproject.exceptions import PyProjectException
from poetry.factory import Factory


@pytest.fixture()
def tester(command_tester_factory):
    return command_tester_factory("config")


def test_show_config_with_local_config_file_empty(tester, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.patch(
        "poetry.factory.Factory.create_poetry",
        side_effect=PyProjectException("[tool.poetry] section not found"),
    )
    tester.execute()

<<<<<<< HEAD
    assert tester.io.fetch_output() == ""


def test_list_displays_default_value_if_not_set(
    tester: "CommandTester", config: "Config", config_cache_dir: "Path"
):
    tester.execute("--list")

    cache_dir = json.dumps(str(config_cache_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
experimental.new-installer = true
installer.max-workers = null
=======
    assert "" == tester.io.fetch_output()


def test_list_displays_default_value_if_not_set(tester, config, config_cache_dir):
    tester.execute("--list")

    expected = """cache-dir = {cache}
experimental.new-installer = true
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
installer.parallel = true
virtualenvs.create = true
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.system-site-packages = false
<<<<<<< HEAD
virtualenvs.path = {venv_path}  # {config_cache_dir / 'virtualenvs'}
"""
=======
virtualenvs.path = {path}  # {virtualenvs}
""".format(
        cache=json.dumps(str(config_cache_dir)),
        path=json.dumps(os.path.join("{cache-dir}", "virtualenvs")),
        virtualenvs=str(config_cache_dir / "virtualenvs"),
    )
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

    assert expected == tester.io.fetch_output()


<<<<<<< HEAD
def test_list_displays_set_get_setting(
    tester: "CommandTester", config: "Config", config_cache_dir: "Path"
):
=======
def test_list_displays_set_get_setting(tester, config, config_cache_dir):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute("virtualenvs.create false")

    tester.execute("--list")

<<<<<<< HEAD
    cache_dir = json.dumps(str(config_cache_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
experimental.new-installer = true
installer.max-workers = null
=======
    expected = """cache-dir = {cache}
experimental.new-installer = true
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
installer.parallel = true
virtualenvs.create = false
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.system-site-packages = false
<<<<<<< HEAD
virtualenvs.path = {venv_path}  # {config_cache_dir / 'virtualenvs'}
"""

    assert config.set_config_source.call_count == 0
    assert expected == tester.io.fetch_output()


def test_display_single_setting(tester: "CommandTester", config: "Config"):
=======
virtualenvs.path = {path}  # {virtualenvs}
""".format(
        cache=json.dumps(str(config_cache_dir)),
        path=json.dumps(os.path.join("{cache-dir}", "virtualenvs")),
        virtualenvs=str(config_cache_dir / "virtualenvs"),
    )

    assert 0 == config.set_config_source.call_count
    assert expected == tester.io.fetch_output()


def test_display_single_setting(tester, config):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute("virtualenvs.create")

    expected = """true
"""

    assert expected == tester.io.fetch_output()


<<<<<<< HEAD
def test_display_single_local_setting(
    command_tester_factory: "CommandTesterFactory", fixture_dir: "FixtureDirGetter"
):
=======
def test_display_single_local_setting(command_tester_factory, fixture_dir):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester = command_tester_factory(
        "config", poetry=Factory().create_poetry(fixture_dir("with_local_config"))
    )
    tester.execute("virtualenvs.create")

    expected = """false
"""

    assert expected == tester.io.fetch_output()


<<<<<<< HEAD
def test_list_displays_set_get_local_setting(
    tester: "CommandTester", config: "Config", config_cache_dir: "Path"
):
=======
def test_list_displays_set_get_local_setting(tester, config, config_cache_dir):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute("virtualenvs.create false --local")

    tester.execute("--list")

<<<<<<< HEAD
    cache_dir = json.dumps(str(config_cache_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
experimental.new-installer = true
installer.max-workers = null
=======
    expected = """cache-dir = {cache}
experimental.new-installer = true
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
installer.parallel = true
virtualenvs.create = false
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.system-site-packages = false
<<<<<<< HEAD
virtualenvs.path = {venv_path}  # {config_cache_dir / 'virtualenvs'}
"""

    assert config.set_config_source.call_count == 1
    assert expected == tester.io.fetch_output()


def test_set_pypi_token(
    tester: "CommandTester", auth_config_source: "DictConfigSource"
):
    tester.execute("pypi-token.pypi mytoken")
    tester.execute("--list")

    assert auth_config_source.config["pypi-token"]["pypi"] == "mytoken"


def test_set_client_cert(
    tester: "CommandTester",
    auth_config_source: "DictConfigSource",
    mocker: "MockerFixture",
):
=======
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
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.spy(ConfigSource, "__init__")

    tester.execute("certificates.foo.client-cert path/to/cert.pem")

    assert (
<<<<<<< HEAD
        auth_config_source.config["certificates"]["foo"]["client-cert"]
        == "path/to/cert.pem"
    )


def test_set_cert(
    tester: "CommandTester",
    auth_config_source: "DictConfigSource",
    mocker: "MockerFixture",
):
=======
        "path/to/cert.pem"
        == auth_config_source.config["certificates"]["foo"]["client-cert"]
    )


def test_set_cert(tester, auth_config_source, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.spy(ConfigSource, "__init__")

    tester.execute("certificates.foo.cert path/to/ca.pem")

<<<<<<< HEAD
    assert auth_config_source.config["certificates"]["foo"]["cert"] == "path/to/ca.pem"


def test_config_installer_parallel(
    tester: "CommandTester", command_tester_factory: "CommandTesterFactory"
):
=======
    assert "path/to/ca.pem" == auth_config_source.config["certificates"]["foo"]["cert"]


def test_config_installer_parallel(tester, command_tester_factory):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
