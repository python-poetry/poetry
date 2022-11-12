from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.core.packages.package import Package

from poetry.__version__ import __version__
from poetry.repositories import RepositoryPool
from poetry.utils.env import EnvManager


if TYPE_CHECKING:
    import httpretty

    from pytest_mock import MockerFixture

    from poetry.repositories.repository import Repository
    from poetry.utils.env import VirtualEnv
    from tests.helpers import TestRepository


@pytest.fixture(autouse=True)
def _patch_repos(repo: TestRepository, installed: Repository) -> None:
    poetry = Package("poetry", __version__)
    repo.add_package(poetry)
    installed.add_package(poetry)


@pytest.fixture(autouse=True)
def save_environ(environ: None) -> Repository:
    yield


@pytest.fixture()
def pool(repo: TestRepository) -> RepositoryPool:
    return RepositoryPool([repo])


@pytest.fixture(autouse=True)
def setup_mocks(
    mocker: MockerFixture,
    tmp_venv: VirtualEnv,
    installed: Repository,
    pool: RepositoryPool,
    http: type[httpretty.httpretty],
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
