from __future__ import annotations

import logging
import sys

from typing import TYPE_CHECKING

import entrypoints

from poetry.plugins.application_plugin import ApplicationPlugin
from poetry.plugins.plugin import Plugin


if TYPE_CHECKING:
    from typing import Any

    from poetry.utils.env import Env


logger = logging.getLogger(__name__)


class PluginManager:
    """
    This class registers and activates plugins.
    """

    def __init__(self, group: str, disable_plugins: bool = False) -> None:
        self._group = group
        self._disable_plugins = disable_plugins
        self._plugins: list[Plugin] = []

    def load_plugins(self, env: Env | None = None) -> None:
        if self._disable_plugins:
            return

        plugin_entrypoints = self.get_plugin_entry_points(env=env)

        for entrypoint in plugin_entrypoints:
            self._load_plugin_entrypoint(entrypoint)

    def get_plugin_entry_points(
        self, env: Env | None = None
    ) -> list[entrypoints.EntryPoint]:
        from poetry.utils.env import EnvManager

        EnvManager.load_project_plugins()

        entry_points: list[entrypoints.EntryPoint] = entrypoints.get_group_all(
            self._group, path=env.sys_path if env else sys.path
        )
        return entry_points

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
