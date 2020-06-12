import logging

import entrypoints

from .application_plugin import ApplicationPlugin
from .plugin import Plugin


logger = logging.getLogger(__name__)


class PluginManager(object):
    """
    This class registers and activates plugins.
    """

    def __init__(self, type, disable_plugins=False):  # type: (str, bool) -> None
        self._type = type
        self._disable_plugins = disable_plugins
        self._plugins = []

    def load_plugins(self):  # type: () -> None
        if self._disable_plugins:
            return

        plugin_entrypoints = entrypoints.get_group_all("poetry.{}".format(self._type))

        for entrypoint in plugin_entrypoints:
            self._load_plugin_entrypoint(entrypoint)

    def add_plugin(self, plugin):  # type: (Plugin) -> None
        if not isinstance(plugin, (Plugin, ApplicationPlugin)):
            raise ValueError(
                "The Poetry plugin must be an instance of Plugin or ApplicationPlugin"
            )

        self._plugins.append(plugin)

    def activate(self, *args, **kwargs):
        for plugin in self._plugins:
            plugin.activate(*args, **kwargs)

    def _load_plugin_entrypoint(
        self, entrypoint
    ):  # type: (entrypoints.EntryPoint) -> None
        logger.debug("Loading the {} plugin".format(entrypoint.name))

        plugin = entrypoint.load()

        if not issubclass(plugin, (Plugin, ApplicationPlugin)):
            raise ValueError(
                "The Poetry plugin must be an instance of Plugin or ApplicationPlugin"
            )

        self.add_plugin(plugin())
