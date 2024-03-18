from __future__ import annotations

import sys

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.factory import Factory
from poetry.puzzle.exceptions import SolverProblemError
from poetry.puzzle.provider import IncompatibleConstraintsError
from poetry.repositories import RepositoryPool
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils.env import ephemeral_environment
from poetry.utils.isolated_build import IsolatedBuildInstallError
from poetry.utils.isolated_build import IsolatedEnv
from tests.helpers import get_dependency


if TYPE_CHECKING:
    from collections.abc import Collection

    from pytest_mock import MockerFixture

    from poetry.repositories.pypi_repository import PyPiRepository


@pytest.fixture()
def pool(pypi_repository: PyPiRepository) -> RepositoryPool:
    pool = RepositoryPool()

    pool.add_repository(pypi_repository)

    return pool


@pytest.fixture(autouse=True)
def setup(mocker: MockerFixture, pool: RepositoryPool) -> None:
    mocker.patch.object(Factory, "create_pool", return_value=pool)


def test_isolated_env_install_success(pool: RepositoryPool) -> None:
    with ephemeral_environment(Path(sys.executable)) as venv:
        env = IsolatedEnv(venv, pool)
        assert not InstalledRepository.load(venv).find_packages(
            get_dependency("poetry-core")
        )

        env.install({"poetry-core"})
        assert InstalledRepository.load(venv).find_packages(
            get_dependency("poetry-core")
        )


@pytest.mark.parametrize(
    ("requirements", "exception"),
    [
        ({"poetry-core==1.5.0", "poetry-core==1.6.0"}, IncompatibleConstraintsError),
        ({"black==19.10b0", "attrs==17.4.0"}, SolverProblemError),
    ],
)
def test_isolated_env_install_error(
    requirements: Collection[str], exception: type[Exception], pool: RepositoryPool
) -> None:
    with ephemeral_environment(Path(sys.executable)) as venv:
        env = IsolatedEnv(venv, pool)
        with pytest.raises(exception):
            env.install(requirements)


def test_isolated_env_install_failure(
    pool: RepositoryPool, mocker: MockerFixture
) -> None:
    mocker.patch("poetry.installation.installer.Installer.run", return_value=1)
    with ephemeral_environment(Path(sys.executable)) as venv:
        env = IsolatedEnv(venv, pool)
        with pytest.raises(IsolatedBuildInstallError) as e:
            env.install({"a", "b>1"})
        assert e.value.requirements == {"a", "b>1"}
