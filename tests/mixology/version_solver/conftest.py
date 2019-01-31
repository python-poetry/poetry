import pytest

from clikit.io import NullIO
from poetry.packages.project_package import ProjectPackage
from poetry.repositories import Pool
from poetry.repositories import Repository

from poetry.puzzle.provider import Provider


@pytest.fixture
def repo():
    return Repository()


@pytest.fixture
def pool(repo):
    pool = Pool()
    pool.add_repository(repo)

    return pool


@pytest.fixture
def root():
    return ProjectPackage("myapp", "0.0.0")


@pytest.fixture
def provider(pool, root):
    return Provider(root, pool, NullIO())
