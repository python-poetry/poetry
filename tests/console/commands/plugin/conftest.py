from typing import TYPE_CHECKING

import pytest

from poetry.core.packages.package import Package

from poetry.__version__ import __version__
from poetry.factory import Factory
from poetry.repositories.installed_repository import InstalledRepository
from poetry.repositories.pool import Pool
from poetry.utils.env import EnvManager


if TYPE_CHECKING:
    from cleo.io.io import IO
    from pytest_mock import MockerFixture

    from poetry.config.config import Config
    from poetry.config.source import Source
    from poetry.poetry import Poetry
    from poetry.repositories import Repository
    from poetry.utils.env import MockEnv
    from tests.helpers import TestRepository
    from tests.types import SourcesFactory


@pytest.fixture()
def installed() -> InstalledRepository:
    repository = InstalledRepository()

    repository.add_package(Package("poetry", __version__))

    return repository


def configure_sources_factory(repo: "TestRepository") -> "SourcesFactory":
    def _configure_sources(
        poetry: "Poetry", sources: "Source", config: "Config", io: "IO"
    ) -> None:
        pool = Pool()
        pool.add_repository(repo)
        poetry.set_pool(pool)

    return _configure_sources


@pytest.fixture(autouse=True)
def setup_mocks(
    mocker: "MockerFixture",
    env: "MockEnv",
    repo: "TestRepository",
    installed: "Repository",
) -> None:
    mocker.patch.object(EnvManager, "get_system_env", return_value=env)
    mocker.patch.object(InstalledRepository, "load", return_value=installed)
    mocker.patch.object(
        Factory, "configure_sources", side_effect=configure_sources_factory(repo)
    )
