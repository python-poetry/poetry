from __future__ import absolute_import
from __future__ import unicode_literals

from clikit.api.event import EventDispatcher

from .__version__ import __version__
from .config.config import Config
from .packages import Locker
from .packages import ProjectPackage
from .plugins import PluginManager
from .repositories.pool import Pool
from .utils._compat import Path
from .utils.toml_file import TomlFile


class Poetry:

    VERSION = __version__

    def __init__(
        self,
        file,  # type: Path
        local_config,  # type: dict
        package,  # type: ProjectPackage
        locker,  # type: Locker
        config,  # type: Config
    ):
        self._file = TomlFile(file)
        self._package = package
        self._local_config = local_config
        self._locker = locker
        self._config = config
        self._event_dispatcher = EventDispatcher()
        self._plugin_manager = None
        self._pool = Pool()

    @property
    def file(self):
        return self._file

    @property
    def package(self):  # type: () -> ProjectPackage
        return self._package

    @property
    def local_config(self):  # type: () -> dict
        return self._local_config

    @property
    def locker(self):  # type: () -> Locker
        return self._locker

    @property
    def pool(self):  # type: () -> Pool
        return self._pool

    @property
    def config(self):  # type: () -> Config
        return self._config

    @property
    def event_dispatcher(self):  # type: () -> EventDispatcher
        return self._event_dispatcher

    @property
    def plugin_manager(self):  # type: () -> PluginManager
        return self._plugin_manager

    def set_locker(self, locker):  # type: (Locker) -> Poetry
        self._locker = locker

        return self

    def set_pool(self, pool):  # type: (Pool) -> Poetry
        self._pool = pool

        return self

    def set_config(self, config):  # type: (Config) -> Poetry
        self._config = config

        return self

    def set_event_dispatcher(
        self, event_dispatcher
    ):  # type: (EventDispatcher) -> Poetry
        self._event_dispatcher = event_dispatcher

        return self

    def set_plugin_manager(self, plugin_manager):  # type: (PluginManager) -> Poetry
        self._plugin_manager = plugin_manager

        return self
