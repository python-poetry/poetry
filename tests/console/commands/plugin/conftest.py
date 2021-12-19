from typing import TYPE_CHECKING

import pytest

from poetry.core.packages.package import Package

from poetry.__version__ import __version__
from poetry.factory import Factory
from poetry.repositories.installed_repository import InstalledRepository
from poetry.repositories.pool import Pool
from poetry.utils.env import EnvManager


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from poetry.repositories import Repository
    from poetry.utils.env import MockEnv
    from tests.helpers import TestRepository


@pytest.fixture()
def installed() -> InstalledRepository:
    repository = InstalledRepository()

    repository.add_package(Package("poetry", __version__))

    return repository


@pytest.fixture(autouse=True)
def setup_mocks(
    mocker: "MockerFixture",
    env: "MockEnv",
    repo: "TestRepository",
    installed: "Repository",
) -> None:
    pool = Pool()
    pool.add_repository(repo)

    mocker.patch.object(EnvManager, "get_system_env", return_value=env)
    mocker.patch.object(InstalledRepository, "load", return_value=installed)
    mocker.patch.object(Factory, "create_pool", return_value=pool)
