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

    from poetry.plugins.plugin_config import PluginConfig
    from tests.types import FixtureDirGetter


class SettingsPlugin(Plugin):
    """
    A plugin declaring its own settings as proposed for the plugin API.
    """

    def declare_settings(self, config: PluginConfig) -> None:
        config.define_setting("mirror-url", "https://pypi.org/simple")
        config.define_setting(
            "retries", 3, validator=int_validator, normalizer=int_normalizer
        )
        config.define_setting(
            "enabled", True, validator=boolean_validator, normalizer=boolean_normalizer
        )

    def activate(self, poetry: Poetry, io: IO) -> None:
        self.config = poetry.config.register_plugin(self)
        self.mirror_url = self.config.get("mirror-url")
        self.retries = self.config.get("retries")


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


def test_invalid_plugin_setting_environment_variable_is_rejected_for_any_normalizer(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin_config = config.register_plugin(SettingsPlugin(), name="demo-plugin")
    plugin_config.define_setting(
        "enabled", True, validator=boolean_validator, normalizer=boolean_normalizer
    )

    monkeypatch.setenv("POETRY_PLUGINS_DEMO_PLUGIN_ENABLED", "not-a-boolean")

    with pytest.raises(PoetryError):
        plugin_config.get("enabled")

    monkeypatch.setenv("POETRY_PLUGINS_DEMO_PLUGIN_ENABLED", "true")

    assert plugin_config.get("enabled") is True


def test_secret_plugin_settings_are_marked_as_secret(config: Config) -> None:
    plugin_config = config.register_plugin(SettingsPlugin(), name="demo-plugin")
    plugin_config.define_setting("token", "", secret=True)
    plugin_config.define_setting("mirror-url", "https://pypi.org/simple")

    assert config.is_secret_setting("plugins.demo-plugin.token")
    assert not config.is_secret_setting("plugins.demo-plugin.mirror-url")
    assert not config.is_secret_setting("virtualenvs.create")


def test_plugin_settings_are_registered_when_the_plugin_is_loaded(
    config: Config, mocker: MockerFixture
) -> None:
    mock_metadata_entry_points(mocker, SettingsPlugin)

    PluginManager(Plugin.group).load_plugins()

    plugin_name = canonicalize_name(SettingsPlugin.__module__.split(".", maxsplit=1)[0])
    assert config.has_setting(f"plugins.{plugin_name}.mirror-url")
    assert config.get(f"plugins.{plugin_name}.mirror-url") == "https://pypi.org/simple"
    assert config.get(f"plugins.{plugin_name}.retries") == 3


def test_settings_of_plugins_that_are_no_longer_loaded_are_removed(
    config: Config, mocker: MockerFixture
) -> None:
    mock_metadata_entry_points(mocker, SettingsPlugin)
    manager = PluginManager(Plugin.group)
    manager.load_plugins()

    plugin_name = canonicalize_name(SettingsPlugin.__module__.split(".", maxsplit=1)[0])
    assert config.has_setting(f"plugins.{plugin_name}.mirror-url")

    # the plugin is not available anymore, e.g. because it was uninstalled
    mocker.patch("importlib.metadata.entry_points", return_value=[])
    PluginManager(Plugin.group).load_plugins()

    assert not config.has_setting(f"plugins.{plugin_name}.mirror-url")
    assert config.get(f"plugins.{plugin_name}.mirror-url") is None
    assert config.get(f"plugins.{plugin_name}.retries") is None


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


def test_plugin_can_read_its_settings_in_activate(
    config: Config, fixture_dir: FixtureDirGetter
) -> None:
    project_path = fixture_dir("simple_project")
    poetry = Poetry(
        project_path / "pyproject.toml",
        {},
        ProjectPackage("simple-project", "1.2.3"),
        Locker(project_path / "poetry.lock", {}),
        config,
    )
    plugin = SettingsPlugin()
    plugin.declare_settings(config.register_plugin(plugin))

    plugin.activate(poetry, BufferedIO())

    assert plugin.mirror_url == "https://pypi.org/simple"
    assert plugin.retries == 3


def test_failed_registration_does_not_register_the_setting(config: Config) -> None:
    config.merge({"plugins": {"demo-plugin": "not-a-table"}})
    plugin_config = config.register_plugin(SettingsPlugin(), name="demo-plugin")

    with pytest.raises(PoetryError) as e:
        plugin_config.define_setting("mirror-url", "https://pypi.org/simple")

    assert "plugins.demo-plugin is configured as a non-table value" in str(e.value)
    assert not config.has_setting("plugins.demo-plugin.mirror-url")
    assert config.get("plugins.demo-plugin.mirror-url") is None


def test_mutable_plugin_defaults_are_not_shared_between_configs() -> None:
    default_items = ["a", "b"]

    config1 = Config()
    config1.register_plugin(SettingsPlugin(), name="demo-plugin").define_setting(
        "items", default_items
    )
    config2 = Config()
    config2.register_plugin(SettingsPlugin(), name="demo-plugin").define_setting(
        "items", default_items
    )

    config1.get("plugins.demo-plugin.items").append("c")

    assert default_items == ["a", "b"]
    assert config2.get("plugins.demo-plugin.items") == ["a", "b"]
