from __future__ import annotations

import json
import os

from typing import TYPE_CHECKING

import pytest

from deepdiff import DeepDiff
from poetry.core.pyproject.exceptions import PyProjectException

from poetry.config.config_source import ConfigSource
from poetry.console.commands.install import InstallCommand
from poetry.factory import Factory
from poetry.repositories.legacy_repository import LegacyRepository
from tests.conftest import Config


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.config.dict_config_source import DictConfigSource
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("config")


def test_show_config_with_local_config_file_empty(
    tester: CommandTester, mocker: MockerFixture
) -> None:
    mocker.patch(
        "poetry.factory.Factory.create_poetry",
        side_effect=PyProjectException("[tool.poetry] section not found"),
    )
    tester.execute()

    assert tester.io.fetch_output() == ""


def test_list_displays_default_value_if_not_set(
    tester: CommandTester, config_cache_dir: Path
) -> None:
    tester.execute("--list")

    cache_dir = json.dumps(str(config_cache_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
experimental.system-git-client = false
installer.max-workers = null
installer.modern-installation = true
installer.no-binary = null
installer.parallel = true
keyring.enabled = true
solver.lazy-wheel = true
virtualenvs.create = true
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.no-setuptools = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / 'virtualenvs'}
virtualenvs.prefer-active-python = false
virtualenvs.prompt = "{{project_name}}-py{{python_version}}"
warnings.export = true
"""

    assert tester.io.fetch_output() == expected


def test_list_displays_set_get_setting(
    tester: CommandTester, config: Config, config_cache_dir: Path
) -> None:
    tester.execute("virtualenvs.create false")

    tester.execute("--list")

    cache_dir = json.dumps(str(config_cache_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
experimental.system-git-client = false
installer.max-workers = null
installer.modern-installation = true
installer.no-binary = null
installer.parallel = true
keyring.enabled = true
solver.lazy-wheel = true
virtualenvs.create = false
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.no-setuptools = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / 'virtualenvs'}
virtualenvs.prefer-active-python = false
virtualenvs.prompt = "{{project_name}}-py{{python_version}}"
warnings.export = true
"""

    assert config.set_config_source.call_count == 0  # type: ignore[attr-defined]
    assert tester.io.fetch_output() == expected


def test_cannot_set_with_multiple_values(tester: CommandTester) -> None:
    with pytest.raises(RuntimeError) as e:
        tester.execute("virtualenvs.create false true")

    assert str(e.value) == "You can only pass one value."


def test_cannot_set_invalid_value(tester: CommandTester) -> None:
    with pytest.raises(RuntimeError) as e:
        tester.execute("virtualenvs.create foo")

    assert str(e.value) == '"foo" is an invalid value for virtualenvs.create'


def test_cannot_unset_with_value(tester: CommandTester) -> None:
    with pytest.raises(RuntimeError) as e:
        tester.execute("virtualenvs.create false --unset")

    assert str(e.value) == "You can not combine a setting value with --unset"


def test_unset_setting(
    tester: CommandTester, config: Config, config_cache_dir: Path
) -> None:
    tester.execute("virtualenvs.path /some/path")
    tester.execute("virtualenvs.path --unset")
    tester.execute("--list")
    cache_dir = json.dumps(str(config_cache_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
experimental.system-git-client = false
installer.max-workers = null
installer.modern-installation = true
installer.no-binary = null
installer.parallel = true
keyring.enabled = true
solver.lazy-wheel = true
virtualenvs.create = true
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.no-setuptools = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / 'virtualenvs'}
virtualenvs.prefer-active-python = false
virtualenvs.prompt = "{{project_name}}-py{{python_version}}"
warnings.export = true
"""
    assert config.set_config_source.call_count == 0  # type: ignore[attr-defined]
    assert tester.io.fetch_output() == expected


def test_unset_repo_setting(
    tester: CommandTester, config: Config, config_cache_dir: Path
) -> None:
    tester.execute("repositories.foo.url https://bar.com/simple/")
    tester.execute("repositories.foo.url --unset ")
    tester.execute("--list")
    cache_dir = json.dumps(str(config_cache_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
experimental.system-git-client = false
installer.max-workers = null
installer.modern-installation = true
installer.no-binary = null
installer.parallel = true
keyring.enabled = true
solver.lazy-wheel = true
virtualenvs.create = true
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.no-setuptools = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / 'virtualenvs'}
virtualenvs.prefer-active-python = false
virtualenvs.prompt = "{{project_name}}-py{{python_version}}"
warnings.export = true
"""
    assert config.set_config_source.call_count == 0  # type: ignore[attr-defined]
    assert tester.io.fetch_output() == expected


def test_unset_value_not_exists(tester: CommandTester) -> None:
    with pytest.raises(ValueError) as e:
        tester.execute("foobar --unset")

    assert str(e.value) == "Setting foobar does not exist"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("virtualenvs.create", "true\n"),
        ("repositories.foo.url", "{'url': 'https://bar.com/simple/'}\n"),
    ],
)
def test_display_single_setting(
    tester: CommandTester, value: str, expected: str | bool
) -> None:
    tester.execute("repositories.foo.url https://bar.com/simple/")
    tester.execute(value)

    assert tester.io.fetch_output() == expected


def test_display_single_local_setting(
    command_tester_factory: CommandTesterFactory, fixture_dir: FixtureDirGetter
) -> None:
    tester = command_tester_factory(
        "config", poetry=Factory().create_poetry(fixture_dir("with_local_config"))
    )
    tester.execute("virtualenvs.create")

    expected = """false
"""

    assert tester.io.fetch_output() == expected


def test_display_empty_repositories_setting(
    command_tester_factory: CommandTesterFactory, fixture_dir: FixtureDirGetter
) -> None:
    tester = command_tester_factory(
        "config",
        poetry=Factory().create_poetry(fixture_dir("with_local_config")),
    )
    tester.execute("repositories")

    expected = """{}
"""
    assert tester.io.fetch_output() == expected


@pytest.mark.parametrize(
    ("setting", "expected"),
    [
        ("repositories", "You cannot remove the [repositories] section"),
        ("repositories.test", "There is no test repository defined"),
    ],
)
def test_unset_nonempty_repositories_section(
    tester: CommandTester, setting: str, expected: str
) -> None:
    tester.execute("repositories.foo.url https://bar.com/simple/")

    with pytest.raises(ValueError) as e:
        tester.execute(f"{setting} --unset")

    assert str(e.value) == expected


def test_set_malformed_repositories_setting(
    tester: CommandTester,
) -> None:
    with pytest.raises(ValueError) as e:
        tester.execute("repositories.foo bar baz")

    assert (
        str(e.value) == "You must pass the url. Example: poetry config repositories.foo"
        " https://bar.com"
    )


@pytest.mark.parametrize(
    ("setting", "expected"),
    [
        ("repositories.foo", "There is no foo repository defined"),
        ("foo", "There is no foo setting."),
    ],
)
def test_display_undefined_setting(
    tester: CommandTester, setting: str, expected: str
) -> None:
    with pytest.raises(ValueError) as e:
        tester.execute(setting)

    assert str(e.value) == expected


def test_list_displays_set_get_local_setting(
    tester: CommandTester, config: Config, config_cache_dir: Path
) -> None:
    tester.execute("virtualenvs.create false --local")

    tester.execute("--list")

    cache_dir = json.dumps(str(config_cache_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
experimental.system-git-client = false
installer.max-workers = null
installer.modern-installation = true
installer.no-binary = null
installer.parallel = true
keyring.enabled = true
solver.lazy-wheel = true
virtualenvs.create = false
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.no-setuptools = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / 'virtualenvs'}
virtualenvs.prefer-active-python = false
virtualenvs.prompt = "{{project_name}}-py{{python_version}}"
warnings.export = true
"""

    assert config.set_config_source.call_count == 1  # type: ignore[attr-defined]
    assert tester.io.fetch_output() == expected


def test_list_must_not_display_sources_from_pyproject_toml(
    project_factory: ProjectFactory,
    fixture_dir: FixtureDirGetter,
    command_tester_factory: CommandTesterFactory,
    config_cache_dir: Path,
) -> None:
    source = fixture_dir("with_non_default_source_implicit")
    pyproject_content = (source / "pyproject.toml").read_text(encoding="utf-8")
    poetry = project_factory("foo", pyproject_content=pyproject_content)
    tester = command_tester_factory("config", poetry=poetry)

    tester.execute("--list")

    cache_dir = json.dumps(str(config_cache_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
experimental.system-git-client = false
installer.max-workers = null
installer.modern-installation = true
installer.no-binary = null
installer.parallel = true
keyring.enabled = true
repositories.foo.url = "https://foo.bar/simple/"
solver.lazy-wheel = true
virtualenvs.create = true
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.no-setuptools = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / 'virtualenvs'}
virtualenvs.prefer-active-python = false
virtualenvs.prompt = "{{project_name}}-py{{python_version}}"
warnings.export = true
"""

    assert tester.io.fetch_output() == expected


def test_set_http_basic(
    tester: CommandTester, auth_config_source: DictConfigSource
) -> None:
    tester.execute("http-basic.foo username password")
    tester.execute("--list")

    assert auth_config_source.config["http-basic"]["foo"] == {
        "username": "username",
        "password": "password",
    }


def test_unset_http_basic(
    tester: CommandTester, auth_config_source: DictConfigSource
) -> None:
    tester.execute("http-basic.foo username password")
    tester.execute("http-basic.foo --unset")
    tester.execute("--list")

    assert "foo" not in auth_config_source.config["http-basic"]


def test_set_http_basic_unsuccessful_multiple_values(
    tester: CommandTester,
) -> None:
    with pytest.raises(ValueError) as e:
        tester.execute("http-basic.foo username password password")

    assert str(e.value) == "Expected one or two arguments (username, password), got 3"


def test_set_pypi_token(
    tester: CommandTester, auth_config_source: DictConfigSource
) -> None:
    tester.execute("pypi-token.pypi mytoken")
    tester.execute("--list")

    assert auth_config_source.config["pypi-token"]["pypi"] == "mytoken"


def test_unset_pypi_token(
    tester: CommandTester, auth_config_source: DictConfigSource
) -> None:
    tester.execute("pypi-token.pypi mytoken")
    tester.execute("pypi-token.pypi --unset")
    tester.execute("--list")

    assert "pypi" not in auth_config_source.config["pypi-token"]


def test_set_pypi_token_unsuccessful_multiple_values(
    tester: CommandTester,
) -> None:
    with pytest.raises(ValueError) as e:
        tester.execute("pypi-token.pypi mytoken mytoken")

    assert str(e.value) == "Expected only one argument (token), got 2"


def test_set_pypi_token_no_values(
    tester: CommandTester,
) -> None:
    with pytest.raises(ValueError) as e:
        tester.execute("pypi-token.pypi")

    assert str(e.value) == "Expected a value for pypi-token.pypi setting."


def test_set_client_cert(
    tester: CommandTester,
    auth_config_source: DictConfigSource,
    mocker: MockerFixture,
) -> None:
    mocker.spy(ConfigSource, "__init__")

    tester.execute("certificates.foo.client-cert path/to/cert.pem")

    assert (
        auth_config_source.config["certificates"]["foo"]["client-cert"]
        == "path/to/cert.pem"
    )


def test_set_client_cert_unsuccessful_multiple_values(
    tester: CommandTester,
    mocker: MockerFixture,
) -> None:
    mocker.spy(ConfigSource, "__init__")

    with pytest.raises(ValueError) as e:
        tester.execute("certificates.foo.client-cert path/to/cert.pem path/to/cert.pem")

    assert str(e.value) == "You must pass exactly 1 value"


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
) -> None:
    mocker.spy(ConfigSource, "__init__")

    tester.execute(f"certificates.foo.cert {value}")

    assert auth_config_source.config["certificates"]["foo"]["cert"] == result


def test_unset_cert(
    tester: CommandTester,
    auth_config_source: DictConfigSource,
    mocker: MockerFixture,
) -> None:
    mocker.spy(ConfigSource, "__init__")

    tester.execute("certificates.foo.cert path/to/ca.pem")

    assert "cert" in auth_config_source.config["certificates"]["foo"]

    tester.execute("certificates.foo.cert --unset")
    assert "cert" not in auth_config_source.config["certificates"]["foo"]


def test_config_installer_parallel(
    tester: CommandTester, command_tester_factory: CommandTesterFactory
) -> None:
    tester.execute("--local installer.parallel")
    assert tester.io.fetch_output().strip() == "true"

    command = command_tester_factory("install")._command
    assert isinstance(command, InstallCommand)
    workers = command.installer._executor._max_workers
    assert workers > 1

    tester.io.clear_output()
    tester.execute("--local installer.parallel false")
    tester.execute("--local installer.parallel")
    assert tester.io.fetch_output().strip() == "false"

    command = command_tester_factory("install")._command
    assert isinstance(command, InstallCommand)
    workers = command.installer._executor._max_workers
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


def test_config_solver_lazy_wheel(
    tester: CommandTester, command_tester_factory: CommandTesterFactory
) -> None:
    tester.execute("--local solver.lazy-wheel")
    assert tester.io.fetch_output().strip() == "true"

    repo = LegacyRepository("foo", "https://foo.com")
    assert repo._lazy_wheel

    tester.io.clear_output()
    tester.execute("--local solver.lazy-wheel false")
    tester.execute("--local solver.lazy-wheel")
    assert tester.io.fetch_output().strip() == "false"

    repo = LegacyRepository("foo", "https://foo.com")
    assert not repo._lazy_wheel
