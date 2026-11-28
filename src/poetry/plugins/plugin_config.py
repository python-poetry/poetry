from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from packaging.utils import canonicalize_name

from poetry.config.config import PLUGIN_SETTINGS_SECTION
from poetry.config.config import ConfigSetting


if TYPE_CHECKING:
    from collections.abc import Callable

    from poetry.config.config import Config


def _accept_any_value(value: str) -> bool:
    return True


def _keep_value_as_is(value: str) -> Any:
    return value


class PluginConfig:
    """
    Configuration of a single plugin.

    Plugins can declare their own settings, which are scoped to
    "plugins.<plugin name>.<setting key>", so that they do not clash with
    Poetry's core settings. Declared settings can be read by the plugin and
    configured by users like any other Poetry setting.
    """

    def __init__(self, config: Config, name: str) -> None:
        self._config = config
        self._name = canonicalize_name(name)

    @property
    def name(self) -> str:
        """
        Name the plugin's settings are scoped to.
        """
        return self._name

    def define_setting(
        self,
        key: str,
        default: Any = None,
        validator: Callable[[str], bool] | None = None,
        normalizer: Callable[[str], Any] | None = None,
        secret: bool = False,
    ) -> None:
        """
        Declare one of the plugin's settings with a default value.

        The validator and the normalizer are used when the setting is set,
        e.g. with "poetry config" or an environment variable. The default
        value is only used if the setting is not configured already, e.g. in
        the user's or the project's configuration file.

        A setting that holds a secret, e.g. a token, should be marked as
        secret so that it is not shown in the output of "poetry config
        --list" and cannot be read with "poetry config <key>".
        """
        self._config.add_plugin_setting(
            self._name,
            key,
            default,
            ConfigSetting(
                validator or _accept_any_value,
                normalizer or _keep_value_as_is,
                secret,
            ),
        )

    def get(self, key: str, default: Any = None) -> Any:
        """
        Return the value of one of the plugin's settings.
        """
        return self._config.get(
            f"{PLUGIN_SETTINGS_SECTION}.{self._name}.{key}", default
        )
