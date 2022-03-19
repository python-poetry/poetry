from __future__ import annotations

import logging

from typing import Any

import entrypoints

from poetry.plugins.application_plugin import ApplicationPlugin
from poetry.plugins.plugin import Plugin


logger = logging.getLogger(__name__)


class PluginManager:
    """
    This class registers and activates plugins.
    """

    def __init__(self, type: str, disable_plugins: bool = False) -> None:
        self._type = type
        self._disable_plugins = disable_plugins
        self._plugins: list[Plugin] = []

    def load_plugins(self) -> None:
        if self._disable_plugins:
            return

        plugin_entrypoints = self.get_plugin_entry_points()

        for entrypoint in plugin_entrypoints:
            self._load_plugin_entrypoint(entrypoint)

    def get_plugin_entry_points(self) -> list[entrypoints.EntryPoint]:
        return entrypoints.get_group_all(f"poetry.{self._type}")

    def add_plugin(self, plugin: Plugin) -> None:
        if not isinstance(plugin, (Plugin, ApplicationPlugin)):
            raise ValueError(
                "The Poetry plugin must be an instance of Plugin or ApplicationPlugin"
            )

        self._plugins.append(plugin)

    def activate(self, *args: Any, **kwargs: Any) -> None:
        for plugin in self._plugins:
            plugin.activate(*args, **kwargs)

    def _load_plugin_entrypoint(self, entrypoint: entrypoints.EntryPoint) -> None:
        logger.debug(f"Loading the {entrypoint.name} plugin")

        plugin = entrypoint.load()

        if not issubclass(plugin, (Plugin, ApplicationPlugin)):
            raise ValueError(
                "The Poetry plugin must be an instance of Plugin or ApplicationPlugin"
            )

        self.add_plugin(plugin())
