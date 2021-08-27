<<<<<<< HEAD
from typing import TYPE_CHECKING

import pytest

from cleo.io.null_io import NullIO
from poetry.core.packages.project_package import ProjectPackage

=======
import pytest

from cleo.io.null_io import NullIO

from poetry.core.packages.project_package import ProjectPackage
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
from poetry.puzzle.provider import Provider as BaseProvider
from poetry.repositories import Pool
from poetry.repositories import Repository


<<<<<<< HEAD
if TYPE_CHECKING:
    from tests.helpers import TestRepository


class Provider(BaseProvider):
    def set_package_python_versions(self, python_versions: str) -> None:
=======
class Provider(BaseProvider):
    def set_package_python_versions(self, python_versions):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        self._package.python_versions = python_versions
        self._python_constraint = self._package.python_constraint


@pytest.fixture
<<<<<<< HEAD
def repo() -> Repository:
=======
def repo():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return Repository()


@pytest.fixture
<<<<<<< HEAD
def pool(repo: "TestRepository") -> Pool:
=======
def pool(repo):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    pool = Pool()
    pool.add_repository(repo)

    return pool


@pytest.fixture
<<<<<<< HEAD
def root() -> ProjectPackage:
=======
def root():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return ProjectPackage("myapp", "0.0.0")


@pytest.fixture
<<<<<<< HEAD
def provider(pool: Pool, root: ProjectPackage) -> Provider:
=======
def provider(pool, root):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return Provider(root, pool, NullIO())
