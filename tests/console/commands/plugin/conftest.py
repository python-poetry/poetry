import pytest

from poetry.__version__ import __version__
from poetry.core.packages.package import Package
from poetry.factory import Factory
from poetry.repositories.installed_repository import InstalledRepository
from poetry.repositories.pool import Pool
from poetry.utils.env import EnvManager


@pytest.fixture()
def installed():
    repository = InstalledRepository()

    repository.add_package(Package("poetry", __version__))

    return repository


def create_pool_factory(repo):
    def _create_pool(config, io):  # noqa
        pool = Pool()
        pool.add_repository(repo)

        return pool

    return _create_pool


@pytest.fixture(autouse=True)
def setup_mocks(mocker, env, repo, installed):
    mocker.patch.object(EnvManager, "get_system_env", return_value=env)
    mocker.patch.object(InstalledRepository, "load", return_value=installed)
    mocker.patch.object(Factory, "create_pool", side_effect=create_pool_factory(repo))
