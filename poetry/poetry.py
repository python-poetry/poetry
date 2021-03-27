from pathlib import Path
from typing import TYPE_CHECKING

from poetry.core.poetry import Poetry as BasePoetry

from .__version__ import __version__


if TYPE_CHECKING:
    from poetry.core.packages.project_package import ProjectPackage

    from .config.config import Config
    from .packages.locker import Locker
    from .repositories.pool import Pool


class Poetry(BasePoetry):

    VERSION = __version__

    def __init__(
        self,
        file: Path,
        local_config: dict,
        package: "ProjectPackage",
        locker: "Locker",
        config: "Config",
    ):
        from .repositories.pool import Pool  # noqa

        super(Poetry, self).__init__(file, local_config, package)

        self._locker = locker
        self._config = config
        self._pool = Pool()

    @property
    def locker(self) -> "Locker":
        return self._locker

    @property
    def pool(self) -> "Pool":
        return self._pool

    @property
    def config(self) -> "Config":
        return self._config

    def set_locker(self, locker: "Locker") -> "Poetry":
        self._locker = locker

        return self

    def set_pool(self, pool: "Pool") -> "Poetry":
        self._pool = pool

        return self

    def set_config(self, config: "Config") -> "Poetry":
        self._config = config

        return self
