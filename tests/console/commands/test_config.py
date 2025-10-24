from __future__ import annotations

import json
import os
import textwrap

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from deepdiff.diff import DeepDiff
from poetry.core.pyproject.exceptions import PyProjectError

from poetry.config.config_source import ConfigSource
from poetry.config.config_source import PropertyNotFoundError
from poetry.console.commands.config import ConfigCommand
from poetry.console.commands.install import InstallCommand
from poetry.factory import Factory
from poetry.repositories.legacy_repository import LegacyRepository
from tests.conftest import Config
from tests.helpers import flatten_dict


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.config.dict_config_source import DictConfigSource
    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("config")


def test_config_command_in_sync_with_config_class() -> None:
    assert set(ConfigCommand().unique_config_values) == set(
        flatten_dict(Config.default_config)
    )


def test_show_config_with_local_config_file_empty(
    tester: CommandTester, mocker: MockerFixture
) -> None:
    mocker.patch(
        "poetry.factory.Factory.create_poetry",
        side_effect=PyProjectError("[tool.poetry] section not found"),
    )
    tester.execute()

    assert tester.io.fetch_output() == ""


def test_list_displays_default_value_if_not_set(
    tester: CommandTester, config_cache_dir: Path, config_data_dir: Path
) -> None:
    tester.execute("--list")

    cache_dir = json.dumps(str(config_cache_dir))
    data_dir = json.dumps(str(config_data_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
data-dir = {data_dir}
installer.max-workers = null
installer.no-binary = null
installer.only-binary = null
installer.parallel = true
installer.re-resolve = true
keyring.enabled = true
python.installation-dir = {json.dumps(str(Path("{data-dir}/python")))}  # {config_data_dir / "python"}
requests.max-retries = 0
solver.lazy-wheel = true
system-git-client = false
virtualenvs.create = true
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / "virtualenvs"}
virtualenvs.prompt = "{{project_name}}-py{{python_version}}"
virtualenvs.use-poetry-python = false
"""

    assert tester.io.fetch_output() == expected


def test_list_displays_set_get_setting(
    tester: CommandTester, config: Config, config_cache_dir: Path, config_data_dir: Path
) -> None:
    tester.execute("virtualenvs.create false")

    tester.execute("--list")

    cache_dir = json.dumps(str(config_cache_dir))
    data_dir = json.dumps(str(config_data_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
data-dir = {data_dir}
installer.max-workers = null
installer.no-binary = null
installer.only-binary = null
installer.parallel = true
installer.re-resolve = true
keyring.enabled = true
python.installation-dir = {json.dumps(str(Path("{data-dir}/python")))}  # {config_data_dir / "python"}
requests.max-retries = 0
solver.lazy-wheel = true
system-git-client = false
virtualenvs.create = false
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / "virtualenvs"}
virtualenvs.prompt = "{{project_name}}-py{{python_version}}"
virtualenvs.use-poetry-python = false
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
    tester: CommandTester, config: Config, config_cache_dir: Path, config_data_dir: Path
) -> None:
    tester.execute("virtualenvs.path /some/path")
    tester.execute("virtualenvs.path --unset")
    tester.execute("--list")
    cache_dir = json.dumps(str(config_cache_dir))
    data_dir = json.dumps(str(config_data_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
data-dir = {data_dir}
installer.max-workers = null
installer.no-binary = null
installer.only-binary = null
installer.parallel = true
installer.re-resolve = true
keyring.enabled = true
python.installation-dir = {json.dumps(str(Path("{data-dir}/python")))}  # {config_data_dir / "python"}
requests.max-retries = 0
solver.lazy-wheel = true
system-git-client = false
virtualenvs.create = true
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / "virtualenvs"}
virtualenvs.prompt = "{{project_name}}-py{{python_version}}"
virtualenvs.use-poetry-python = false
"""
    assert config.set_config_source.call_count == 0  # type: ignore[attr-defined]
    assert tester.io.fetch_output() == expected


def test_unset_repo_setting(
    tester: CommandTester, config: Config, config_cache_dir: Path, config_data_dir: Path
) -> None:
    tester.execute("repositories.foo.url https://bar.com/simple/")
    tester.execute("repositories.foo.url --unset ")
    tester.execute("--list")
    cache_dir = json.dumps(str(config_cache_dir))
    data_dir = json.dumps(str(config_data_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
data-dir = {data_dir}
installer.max-workers = null
installer.no-binary = null
installer.only-binary = null
installer.parallel = true
installer.re-resolve = true
keyring.enabled = true
python.installation-dir = {json.dumps(str(Path("{data-dir}/python")))}  # {config_data_dir / "python"}
requests.max-retries = 0
solver.lazy-wheel = true
system-git-client = false
virtualenvs.create = true
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / "virtualenvs"}
virtualenvs.prompt = "{{project_name}}-py{{python_version}}"
virtualenvs.use-poetry-python = false
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
    tester: CommandTester,
    config: Config,
    config_cache_dir: Path,
    config_data_dir: Path,
) -> None:
    tester.execute("virtualenvs.create false --local")

    tester.execute("--list")

    cache_dir = json.dumps(str(config_cache_dir))
    data_dir = json.dumps(str(config_data_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
data-dir = {data_dir}
installer.max-workers = null
installer.no-binary = null
installer.only-binary = null
installer.parallel = true
installer.re-resolve = true
keyring.enabled = true
python.installation-dir = {json.dumps(str(Path("{data-dir}/python")))}  # {config_data_dir / "python"}
requests.max-retries = 0
solver.lazy-wheel = true
system-git-client = false
virtualenvs.create = false
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / "virtualenvs"}
virtualenvs.prompt = "{{project_name}}-py{{python_version}}"
virtualenvs.use-poetry-python = false
"""

    assert config.set_config_source.call_count == 1  # type: ignore[attr-defined]
    assert tester.io.fetch_output() == expected


def test_list_must_not_display_sources_from_pyproject_toml(
    project_factory: ProjectFactory,
    fixture_dir: FixtureDirGetter,
    command_tester_factory: CommandTesterFactory,
    config_cache_dir: Path,
    config_data_dir: Path,
) -> None:
    source = fixture_dir("with_primary_source_implicit")
    pyproject_content = (source / "pyproject.toml").read_text(encoding="utf-8")
    poetry = project_factory("foo", pyproject_content=pyproject_content)
    tester = command_tester_factory("config", poetry=poetry)

    tester.execute("--list")

    cache_dir = json.dumps(str(config_cache_dir))
    data_dir = json.dumps(str(config_data_dir))
    venv_path = json.dumps(os.path.join("{cache-dir}", "virtualenvs"))
    expected = f"""cache-dir = {cache_dir}
data-dir = {data_dir}
installer.max-workers = null
installer.no-binary = null
installer.only-binary = null
installer.parallel = true
installer.re-resolve = true
keyring.enabled = true
python.installation-dir = {json.dumps(str(Path("{data-dir}/python")))}  # {config_data_dir / "python"}
repositories.foo.url = "https://foo.bar/simple/"
requests.max-retries = 0
solver.lazy-wheel = true
system-git-client = false
virtualenvs.create = true
virtualenvs.in-project = null
virtualenvs.options.always-copy = false
virtualenvs.options.no-pip = false
virtualenvs.options.system-site-packages = false
virtualenvs.path = {venv_path}  # {config_cache_dir / "virtualenvs"}
virtualenvs.prompt = "{{project_name}}-py{{python_version}}"
virtualenvs.use-poetry-python = false
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
    ("setting",),
    [
        ("installer.no-binary",),
        ("installer.only-binary",),
    ],
)
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
def test_config_installer_binary_filter_config(
    tester: CommandTester, setting: str, value: str, expected: list[str]
) -> None:
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


current_config = """\
[experimental]
system-git-client = true

[virtualenvs]
prefer-active-python = false
"""

config_migrated = """\
system-git-client = true

[virtualenvs]
use-poetry-python = true
"""


@pytest.mark.parametrize(
    ["proceed", "expected_config"],
    [
        ("yes", config_migrated),
        ("no", current_config),
    ],
)
def test_config_migrate(
    proceed: str,
    expected_config: str,
    tester: CommandTester,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "config"
    mocker.patch("poetry.locations.CONFIG_DIR", config_dir)

    config_file = Path(config_dir / "config.toml")
    with config_file.open("w", encoding="utf-8") as fh:
        fh.write(current_config)

    tester.execute("--migrate", inputs=proceed)

    expected_output = textwrap.dedent("""\
    Checking for required migrations ...
    experimental.system-git-client = true -> system-git-client = true
    virtualenvs.prefer-active-python = false -> virtualenvs.use-poetry-python = true
    """)

    output = tester.io.fetch_output()
    assert output.startswith(expected_output)

    with config_file.open("r", encoding="utf-8") as fh:
        assert fh.read() == expected_config


def test_config_migrate_local_config(tester: CommandTester, poetry: Poetry) -> None:
    local_config = poetry.file.path.parent / "poetry.toml"
    config_data = textwrap.dedent("""\
    [experimental]
    system-git-client = true

    [virtualenvs]
    prefer-active-python = false
    """)

    with local_config.open("w", encoding="utf-8") as fh:
        fh.write(config_data)

    tester.execute("--migrate --local", inputs="yes")

    expected_config = textwrap.dedent("""\
        system-git-client = true

        [virtualenvs]
        use-poetry-python = true
        """)

    with local_config.open("r", encoding="utf-8") as fh:
        assert fh.read() == expected_config


def test_config_migrate_local_config_should_raise_if_not_found(
    tester: CommandTester,
) -> None:
    with pytest.raises(RuntimeError, match="No local config file found"):
        tester.execute("--migrate --local", inputs="yes")


def test_config_installer_build_config_settings(
    tester: CommandTester, config: Config
) -> None:
    config_key = "installer.build-config-settings.demo"
    value = {"CC": "gcc", "--build-option": ["--one", "--two"]}

    tester.execute(f"{config_key} '{json.dumps(value)}'")
    assert not DeepDiff(config.config_source.get_property(config_key), value)

    value_two = {"CC": "g++"}
    tester.execute(f"{config_key} '{json.dumps(value_two)}'")
    assert not DeepDiff(
        config.config_source.get_property(config_key), {**value, **value_two}
    )

    value_three = {
        "--build-option": ["--three", "--four"],
        "--package-option": ["--name=foo"],
    }
    tester.execute(f"{config_key} '{json.dumps(value_three)}'")
    assert not DeepDiff(
        config.config_source.get_property(config_key),
        {
            **value,
            **value_two,
            **value_three,
        },
    )

    tester.execute(f"{config_key} --unset")

    with pytest.raises(PropertyNotFoundError):
        config.config_source.get_property(config_key)


@pytest.mark.parametrize(
    "value",
    [
        "BAD=VALUE",
        "BAD",
        json.dumps({"key": ["str", 0]}),
    ],
)
def test_config_installer_build_config_settings_bad_values(
    value: str, tester: CommandTester
) -> None:
    config_key = "installer.build-config-settings.demo"

    with pytest.raises(ValueError) as e:
        tester.execute(f"{config_key} '{value}'")

    assert str(e.value) == (
        f"Invalid build config setting '{value}'. "
        f"It must be a valid JSON with each property "
        f"a string or a list of strings."
    )


def test_command_config_build_config_settings_get(
    tester: CommandTester, config: Config
) -> None:
    setting_group = "installer.build-config-settings"
    setting = f"{setting_group}.foo"

    # test when no values are configured
    tester.execute(setting)
    assert tester.io.fetch_error() == ""
    assert (
        tester.io.fetch_output().strip()
        == "No build config settings configured for foo."
    )

    tester.execute(setting_group)
    assert tester.io.fetch_error() == ""
    assert (
        tester.io.fetch_output().strip()
        == "No packages configured with build config settings."
    )

    # test with one value configured
    value = {"CC": "gcc", "--build-options": ["--one", "--two"]}
    tester.execute(f"{setting} '{json.dumps(value)}'")
    assert tester.status_code == 0
    assert tester.io.fetch_output() == tester.io.fetch_error() == ""

    tester.execute(setting)
    assert tester.io.fetch_error() == ""
    assert tester.io.fetch_output().strip() == json.dumps(value)

    tester.execute(setting_group)
    assert tester.io.fetch_error() == ""
    assert tester.io.fetch_output().strip().splitlines() == [
        'foo.--build-options = "[--one, --two]"',
        'foo.CC = "gcc"',
    ]

    # test getting un-configured value
    tester.execute(f"{setting_group}.bar")
    assert tester.io.fetch_error() == ""
    assert (
        tester.io.fetch_output().strip()
        == "No build config settings configured for bar."
    )
