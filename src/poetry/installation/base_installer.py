from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from cleo.io.io import IO
    from poetry.core.packages.package import Package

    from poetry.repositories.repository_pool import RepositoryPool
    from poetry.utils.env import Env


class BaseInstaller:
    def __init__(self, env: Env, io: IO, pool: RepositoryPool) -> None:
        self._env = env
        self._io = io
        self._pool = pool

    def install(self, package: Package) -> None:
        raise NotImplementedError

    def update(self, source: Package, target: Package) -> None:
        raise NotImplementedError

    def remove(self, package: Package) -> None:
        raise NotImplementedError
