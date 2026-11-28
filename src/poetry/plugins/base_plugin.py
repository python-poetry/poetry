from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from poetry.plugins.plugin_config import PluginConfig


class BasePlugin(ABC):
    """
    Base class for all plugin types

    The `activate()` method must be implemented and receives the Poetry instance.
    """

    PLUGIN_API_VERSION = "1.0.0"

    @property
    @abstractmethod
    def group(self) -> str:
        """
        Name of entrypoint group the plugin belongs to.
        """

    def declare_settings(self, config: PluginConfig) -> None:  # noqa: B027
        """
        Declare the settings of the plugin.

        This method is called when the plugin is loaded, i.e. before the
        plugin is activated, so that the settings of the plugin are known
        even if the plugin is not activated, e.g. when Poetry is run
        outside of a project.

        This is an optional hook, i.e. the default implementation does not
        declare any settings.
        """
