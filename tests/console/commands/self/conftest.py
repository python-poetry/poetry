from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Callable

import pytest

from poetry.core.packages.package import Package

from poetry.__version__ import __version__
from poetry.factory import Factory
from poetry.repositories import RepositoryPool
from poetry.utils.env import EnvManager


if TYPE_CHECKING:
    from collections.abc import Iterable

    import httpretty

    from cleo.io.io import IO
    from pytest_mock import MockerFixture

    from poetry.config.config import Config
    from poetry.repositories.repository import Repository
    from poetry.utils.env import VirtualEnv
    from tests.helpers import TestRepository


@pytest.fixture(autouse=True)
def _patch_repos(repo: TestRepository, installed: Repository) -> None:
    poetry = Package("poetry", __version__)
    repo.add_package(poetry)
    installed.add_package(poetry)


@pytest.fixture()
def pool(repo: TestRepository) -> RepositoryPool:
    return RepositoryPool([repo])


def create_pool_factory(
    repo: Repository,
) -> Callable[[Config, Iterable[dict[str, Any]], IO, bool], RepositoryPool]:
    def _create_pool(
        config: Config,
        sources: Iterable[dict[str, Any]] = (),
        io: IO | None = None,
        disable_cache: bool = False,
    ) -> RepositoryPool:
        pool = RepositoryPool()
        pool.add_repository(repo)

        return pool

    return _create_pool


@pytest.fixture(autouse=True)
def setup_mocks(
    mocker: MockerFixture,
    tmp_venv: VirtualEnv,
    installed: Repository,
    pool: RepositoryPool,
    http: type[httpretty.httpretty],
    repo: Repository,
) -> None:
    mocker.patch.object(EnvManager, "get_system_env", return_value=tmp_venv)
    mocker.patch(
        "poetry.repositories.repository_pool.RepositoryPool.find_packages",
        pool.find_packages,
    )
    mocker.patch(
        "poetry.repositories.repository_pool.RepositoryPool.package", pool.package
    )
    mocker.patch("poetry.installation.executor.pip_install")
    mocker.patch(
        "poetry.installation.installer.Installer._get_installed",
        return_value=installed,
    )
    mocker.patch.object(Factory, "create_pool", side_effect=create_pool_factory(repo))
