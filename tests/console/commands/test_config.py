from __future__ import annotations

import json
import os

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
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("config")


def test_show_config_with_local_config_file_empty(
    tester: CommandTester, mocker: MockerFixture
):
    mocker.patch(
        "poetry.factory.Factory.create_poetry",
        side_effect=PyProjectException("[tool.poetry] section not found"),
    )
    tester.execute()

    assert tester.io.fetch_output() == ""


def test_list_displays_default_value_if_not_set(
    tester: CommandTester, config: Config, config_cache_dir: Path
):
    tester.execute("--list")

    cache_dir = json.dumps(str(config_cache_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
experimental.new-installer = true
installer.max-workers = null
installer.parallel = true
virtualenvs.create = true
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.no-setuptools = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / 'virtualenvs'}
virtualenvs.prefer-active-python = false
"""

    assert tester.io.fetch_output() == expected


def test_list_displays_set_get_setting(
    tester: CommandTester, config: Config, config_cache_dir: Path
):
    tester.execute("virtualenvs.create false")

    tester.execute("--list")

    cache_dir = json.dumps(str(config_cache_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
experimental.new-installer = true
installer.max-workers = null
installer.parallel = true
virtualenvs.create = false
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.no-setuptools = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / 'virtualenvs'}
virtualenvs.prefer-active-python = false
"""

    assert config.set_config_source.call_count == 0
    assert tester.io.fetch_output() == expected


def test_display_single_setting(tester: CommandTester, config: Config):
    tester.execute("virtualenvs.create")

    expected = """true
"""

    assert tester.io.fetch_output() == expected


def test_display_single_local_setting(
    command_tester_factory: CommandTesterFactory, fixture_dir: FixtureDirGetter
):
    tester = command_tester_factory(
        "config", poetry=Factory().create_poetry(fixture_dir("with_local_config"))
    )
    tester.execute("virtualenvs.create")

    expected = """false
"""

    assert tester.io.fetch_output() == expected


def test_list_displays_set_get_local_setting(
    tester: CommandTester, config: Config, config_cache_dir: Path
):
    tester.execute("virtualenvs.create false --local")

    tester.execute("--list")

    cache_dir = json.dumps(str(config_cache_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
experimental.new-installer = true
installer.max-workers = null
installer.parallel = true
virtualenvs.create = false
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.no-setuptools = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / 'virtualenvs'}
virtualenvs.prefer-active-python = false
"""

    assert config.set_config_source.call_count == 1
    assert tester.io.fetch_output() == expected


def test_set_pypi_token(tester: CommandTester, auth_config_source: DictConfigSource):
    tester.execute("pypi-token.pypi mytoken")
    tester.execute("--list")

    assert auth_config_source.config["pypi-token"]["pypi"] == "mytoken"


def test_set_client_cert(
    tester: CommandTester,
    auth_config_source: DictConfigSource,
    mocker: MockerFixture,
):
    mocker.spy(ConfigSource, "__init__")

    tester.execute("certificates.foo.client-cert path/to/cert.pem")

    assert (
        auth_config_source.config["certificates"]["foo"]["client-cert"]
        == "path/to/cert.pem"
    )


def test_set_cert(
    tester: CommandTester,
    auth_config_source: DictConfigSource,
    mocker: MockerFixture,
):
    mocker.spy(ConfigSource, "__init__")

    tester.execute("certificates.foo.cert path/to/ca.pem")

    assert auth_config_source.config["certificates"]["foo"]["cert"] == "path/to/ca.pem"


def test_config_installer_parallel(
    tester: CommandTester, command_tester_factory: CommandTesterFactory
):
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
