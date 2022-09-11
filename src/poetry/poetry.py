from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from poetry.core.poetry import Poetry as BasePoetry

from poetry.__version__ import __version__
from poetry.config.source import Source


if TYPE_CHECKING:
    from pathlib import Path

    from poetry.core.packages.project_package import ProjectPackage

    from poetry.config.config import Config
    from poetry.packages.locker import Locker
    from poetry.plugins.plugin_manager import PluginManager
    from poetry.repositories.pool import Pool


class Poetry(BasePoetry):
    VERSION = __version__

    def __init__(
        self,
        file: Path,
        local_config: dict[str, Any],
        package: ProjectPackage,
        locker: Locker,
        config: Config,
        disable_cache: bool = False,
    ) -> None:
        from poetry.repositories.pool import Pool

        super().__init__(file, local_config, package)

        self._locker = locker
        self._config = config
        self._pool = Pool()
        self._plugin_manager: PluginManager | None = None
        self._disable_cache = disable_cache

    @property
    def locker(self) -> Locker:
        return self._locker

    @property
    def pool(self) -> Pool:
        return self._pool

    @property
    def config(self) -> Config:
        return self._config

    @property
    def disable_cache(self) -> bool:
        return self._disable_cache

    def set_locker(self, locker: Locker) -> Poetry:
        self._locker = locker

        return self

    def set_pool(self, pool: Pool) -> Poetry:
        self._pool = pool

        return self

    def set_config(self, config: Config) -> Poetry:
        self._config = config

        return self

    def set_plugin_manager(self, plugin_manager: PluginManager) -> Poetry:
        self._plugin_manager = plugin_manager

        return self

    def get_sources(self) -> list[Source]:
        return [
            Source(**source)
            for source in self.pyproject.poetry_config.get("source", [])
        ]
