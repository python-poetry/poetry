from __future__ import absolute_import
from __future__ import unicode_literals

from poetry.core.packages import ProjectPackage
from poetry.core.poetry import Poetry as BasePoetry

from .__version__ import __version__
from .config.config import Config
from .packages import Locker
from .repositories.pool import Pool
from .utils._compat import Path


class Poetry(BasePoetry):

    VERSION = __version__

    def __init__(
        self,
        file,  # type: Path
        local_config,  # type: dict
        package,  # type: ProjectPackage
        locker,  # type: Locker
        config,  # type: Config
    ):
        super(Poetry, self).__init__(file, local_config, package)

        self._locker = locker
        self._config = config
        self._pool = Pool()

    @property
    def locker(self):  # type: () -> Locker
        return self._locker

    @property
    def pool(self):  # type: () -> Pool
        return self._pool

    @property
    def config(self):  # type: () -> Config
        return self._config

    def set_locker(self, locker):  # type: (Locker) -> Poetry
        self._locker = locker

        return self

    def set_pool(self, pool):  # type: (Pool) -> Poetry
        self._pool = pool

        return self

    def set_config(self, config):  # type: (Config) -> Poetry
        self._config = config

        return self
