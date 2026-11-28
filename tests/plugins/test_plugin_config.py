from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cleo.io.buffered_io import BufferedIO
from packaging.utils import canonicalize_name
from poetry.core.packages.project_package import ProjectPackage

from poetry.config.config import Config
from poetry.config.config import boolean_normalizer
from poetry.config.config import boolean_validator
from poetry.config.config import int_normalizer
from poetry.config.config import int_validator
from poetry.exceptions import PoetryError
from poetry.packages.locker import Locker
from poetry.plugins.plugin import Plugin
from poetry.plugins.plugin_manager import PluginManager
from poetry.poetry import Poetry
from tests.helpers import mock_metadata_entry_points


if TYPE_CHECKING:
    from cleo.io.io import IO
    from pytest_mock import MockerFixture

    from tests.types import FixtureDirGetter


class SettingsPlugin(Plugin):
    """
    A plugin declaring its own settings as proposed for the plugin API.
    """

    def activate(self, poetry: Poetry, io: IO) -> None:
        self.config = poetry.config.register_plugin(self)
        self.config.define_setting("mirror-url", "https://pypi.org/simple")
        self.config.define_setting(
            "retries", 3, validator=int_validator, normalizer=int_normalizer
        )
        self.config.define_setting(
            "enabled", True, validator=boolean_validator, normalizer=boolean_normalizer
        )


def test_plugin_settings_are_registered_with_their_default_values(
    config: Config,
) -> None:
    plugin_config = config.register_plugin(SettingsPlugin(), name="demo-plugin")
    plugin_config.define_setting("mirror-url", "https://pypi.org/simple")

    assert config.get("plugins.demo-plugin.mirror-url") == "https://pypi.org/simple"
    assert plugin_config.get("mirror-url") == "https://pypi.org/simple"


def test_plugin_settings_are_part_of_the_full_configuration(config: Config) -> None:
    config.register_plugin(SettingsPlugin(), name="demo-plugin").define_setting(
        "mirror-url", "https://pypi.org/simple"
    )

    assert config.all()["plugins"]["demo-plugin"]["mirror-url"] == (
        "https://pypi.org/simple"
    )


def test_plugin_settings_without_default_value_are_still_listed(
    config: Config,
) -> None:
    plugin_config = config.register_plugin(SettingsPlugin(), name="demo-plugin")
    plugin_config.define_setting("mirror-url")

    assert plugin_config.get("mirror-url") is None
    assert "mirror-url" in config.all()["plugins"]["demo-plugin"]


def test_configured_value_takes_precedence_over_the_plugin_default(
    config: Config,
) -> None:
    config.merge(
        {
            "plugins": {
                "demo-plugin": {"mirror-url": "https://mirror.example.com/simple"}
            }
        }
    )
    plugin_config = config.register_plugin(SettingsPlugin(), name="demo-plugin")
    plugin_config.define_setting("mirror-url", "https://pypi.org/simple")

    assert plugin_config.get("mirror-url") == "https://mirror.example.com/simple"


def test_plugin_settings_coexist_with_core_settings(config: Config) -> None:
    config.merge(
        {
            "virtualenvs": {"create": False},
            "plugins": {"demo-plugin": {"mirror-url": "https://mirror.example.com"}},
        }
    )
    plugin_config = config.register_plugin(SettingsPlugin(), name="demo-plugin")
    plugin_config.define_setting("mirror-url", "https://pypi.org/simple")

    assert config.get("virtualenvs.create") is False
    assert plugin_config.get("mirror-url") == "https://mirror.example.com"
    assert config.get("installer.parallel") is True


def test_plugin_settings_are_not_shared_between_config_instances() -> None:
    config = Config()
    config.register_plugin(SettingsPlugin(), name="demo-plugin").define_setting(
        "mirror-url", "https://pypi.org/simple"
    )

    assert Config().get("plugins.demo-plugin.mirror-url") is None


def test_plugin_settings_are_validated_and_normalized(config: Config) -> None:
    plugin_config = config.register_plugin(SettingsPlugin(), name="demo-plugin")
    plugin_config.define_setting(
        "retries", 3, validator=int_validator, normalizer=int_normalizer
    )

    assert config.get_validator("plugins.demo-plugin.retries")("5")
    assert not config.get_validator("plugins.demo-plugin.retries")("not-a-number")
    assert config.get_normalizer("plugins.demo-plugin.retries")("5") == 5


def test_plugin_setting_values_can_be_set_with_environment_variables(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin_config = config.register_plugin(SettingsPlugin(), name="demo-plugin")
    plugin_config.define_setting(
        "retries", 3, validator=int_validator, normalizer=int_normalizer
    )

    monkeypatch.setenv("POETRY_PLUGINS_DEMO_PLUGIN_RETRIES", "7")

    assert plugin_config.get("retries") == 7


def test_invalid_plugin_setting_environment_variable_is_rejected(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin_config = config.register_plugin(SettingsPlugin(), name="demo-plugin")
    plugin_config.define_setting(
        "retries", 3, validator=int_validator, normalizer=int_normalizer
    )

    monkeypatch.setenv("POETRY_PLUGINS_DEMO_PLUGIN_RETRIES", "not-a-number")

    with pytest.raises(PoetryError):
        plugin_config.get("retries")


def test_plugin_settings_are_scoped_to_the_name_of_the_plugin_package(
    config: Config,
) -> None:
    class MirrorPlugin(Plugin):
        def activate(self, poetry: Poetry, io: IO) -> None:
            pass

    MirrorPlugin.__module__ = "poetry_plugin_pypi_mirror.plugins"

    plugin_config = config.register_plugin(MirrorPlugin())

    assert plugin_config.name == "poetry-plugin-pypi-mirror"

    plugin_config.define_setting("url", "https://pypi.org/simple")

    assert config.get("plugins.poetry-plugin-pypi-mirror.url") == (
        "https://pypi.org/simple"
    )


def test_plugin_settings_are_registered_when_the_plugin_is_activated(
    config: Config, fixture_dir: FixtureDirGetter, mocker: MockerFixture
) -> None:
    project_path = fixture_dir("simple_project")
    poetry = Poetry(
        project_path / "pyproject.toml",
        {},
        ProjectPackage("simple-project", "1.2.3"),
        Locker(project_path / "poetry.lock", {}),
        config,
    )

    mock_metadata_entry_points(mocker, SettingsPlugin)

    manager = PluginManager(Plugin.group)
    manager.load_plugins()
    manager.activate(poetry, BufferedIO())

    # settings are scoped to the name of the package the plugin is defined in
    plugin_name = canonicalize_name(SettingsPlugin.__module__.split(".", maxsplit=1)[0])

    assert config.get(f"plugins.{plugin_name}.mirror-url") == "https://pypi.org/simple"
    assert config.get(f"plugins.{plugin_name}.retries") == 3


def test_plugin_setting_registration_fails_if_the_config_value_is_not_a_table(
    config: Config,
) -> None:
    config.merge({"plugins": {"demo-plugin": "not-a-table"}})
    plugin_config = config.register_plugin(SettingsPlugin(), name="demo-plugin")

    with pytest.raises(PoetryError) as e:
        plugin_config.define_setting("mirror-url", "https://pypi.org/simple")

    assert "plugins.demo-plugin is configured as a non-table value" in str(e.value)
