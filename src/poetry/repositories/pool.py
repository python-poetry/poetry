from __future__ import annotations

import warnings

from typing import TYPE_CHECKING

from poetry.repositories.repository_pool import RepositoryPool


if TYPE_CHECKING:
    from poetry.repositories.repository import Repository


class Pool(RepositoryPool):
    def __init__(
        self,
        repositories: list[Repository] | None = None,
        ignore_repository_names: bool = False,
    ) -> None:
        warnings.warn(
            "Object Pool from poetry.repositories.pool is renamed and scheduled for"
            " removal in poetry release 1.4.0. Please migrate to RepositoryPool from"
            " poetry.repositories.repository_pool.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(repositories, ignore_repository_names)
