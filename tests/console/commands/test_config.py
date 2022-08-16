from __future__ import annotations

import json
import os

from typing import TYPE_CHECKING

import pytest

from deepdiff import DeepDiff
from poetry.core.pyproject.exceptions import PyProjectException

from poetry.config.config_source import ConfigSource
from poetry.factory import Factory
from tests.conftest import Config


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.config.dict_config_source import DictConfigSource
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
experimental.system-git-client = false
installer.max-workers = null
installer.no-binary = null
installer.parallel = true
virtualenvs.create = true
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.no-setuptools = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / 'virtualenvs'}
virtualenvs.prefer-active-python = false
virtualenvs.prompt = "{{project_name}}-py{{python_version}}"
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
experimental.system-git-client = false
installer.max-workers = null
installer.no-binary = null
installer.parallel = true
virtualenvs.create = false
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.no-setuptools = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / 'virtualenvs'}
virtualenvs.prefer-active-python = false
virtualenvs.prompt = "{{project_name}}-py{{python_version}}"
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
experimental.system-git-client = false
installer.max-workers = null
installer.no-binary = null
installer.parallel = true
virtualenvs.create = false
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.no-setuptools = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / 'virtualenvs'}
virtualenvs.prefer-active-python = false
virtualenvs.prompt = "{{project_name}}-py{{python_version}}"
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


@pytest.mark.parametrize(
    ("value", "result"),
    [
        ("path/to/ca.pem", "path/to/ca.pem"),
        ("true", True),
        ("false", False),
    ],
)
def test_set_cert(
    tester: CommandTester,
    auth_config_source: DictConfigSource,
    mocker: MockerFixture,
    value: str,
    result: str | bool,
):
    mocker.spy(ConfigSource, "__init__")

    tester.execute(f"certificates.foo.cert {value}")

    assert auth_config_source.config["certificates"]["foo"]["cert"] == result


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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("true", [":all:"]),
        ("1", [":all:"]),
        ("false", [":none:"]),
        ("0", [":none:"]),
        ("pytest", ["pytest"]),
        ("PyTest", ["pytest"]),
        ("pytest,black", ["pytest", "black"]),
        ("", []),
    ],
)
def test_config_installer_no_binary(
    tester: CommandTester, value: str, expected: list[str]
) -> None:
    setting = "installer.no-binary"

    tester.execute(setting)
    assert tester.io.fetch_output().strip() == "null"

    config = Config.create()
    assert not config.get(setting)

    tester.execute(f"{setting} '{value}'")

    config = Config.create(reload=True)
    assert not DeepDiff(config.get(setting), expected, ignore_order=True)
