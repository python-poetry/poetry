from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cleo.io.null_io import NullIO
from poetry.core.packages.project_package import ProjectPackage

from poetry.puzzle import Solver
from poetry.repositories import Repository
from poetry.repositories import RepositoryPool
from tests.helpers import MOCK_DEFAULT_GIT_REVISION
from tests.helpers import mock_clone


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def setup(mocker: MockerFixture) -> None:
    # Patch git module to not actually clone projects
    mocker.patch("poetry.vcs.git.Git.clone", new=mock_clone)
    p = mocker.patch("poetry.vcs.git.Git.get_revision")
    p.return_value = MOCK_DEFAULT_GIT_REVISION


@pytest.fixture
def io() -> NullIO:
    return NullIO()


@pytest.fixture
def package() -> ProjectPackage:
    return ProjectPackage("root", "1.0")


@pytest.fixture
def repo() -> Repository:
    return Repository("repo")


@pytest.fixture
def pool(repo: Repository) -> RepositoryPool:
    return RepositoryPool([repo])


@pytest.fixture
def solver(package: ProjectPackage, pool: RepositoryPool, io: NullIO) -> Solver:
    return Solver(package, pool, [], [], io)
