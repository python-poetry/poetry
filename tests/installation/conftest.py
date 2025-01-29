from __future__ import annotations

import pytest

from packaging.tags import Tag

from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.pypi_repository import PyPiRepository
from poetry.repositories.repository_pool import RepositoryPool
from poetry.utils.env import MockEnv


@pytest.fixture()
def env() -> MockEnv:
    return MockEnv(
        supported_tags=[
            Tag("cp37", "cp37", "macosx_10_15_x86_64"),
            Tag("py3", "none", "any"),
        ]
    )


@pytest.fixture()
def pool(legacy_repository: LegacyRepository) -> RepositoryPool:
    pool = RepositoryPool()

    pool.add_repository(PyPiRepository(disable_cache=True))
    pool.add_repository(
        LegacyRepository("foo", "https://legacy.foo.bar/simple/", disable_cache=True)
    )
    pool.add_repository(
        LegacyRepository("foo2", "https://legacy.foo2.bar/simple/", disable_cache=True)
    )
    return pool
