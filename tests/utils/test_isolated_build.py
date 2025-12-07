from __future__ import annotations

import shutil
import sys
import uuid

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.core.packages.dependency import Dependency

from poetry.factory import Factory
from poetry.puzzle.exceptions import SolverProblemError
from poetry.puzzle.provider import IncompatibleConstraintsError
from poetry.repositories import RepositoryPool
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils.env import ephemeral_environment
from poetry.utils.isolated_build import CONSTRAINTS_GROUP_NAME
from poetry.utils.isolated_build import IsolatedBuildInstallError
from poetry.utils.isolated_build import IsolatedEnv
from poetry.utils.isolated_build import isolated_builder
from tests.helpers import get_dependency


if TYPE_CHECKING:
    from collections.abc import Collection

    from pytest_mock import MockerFixture

    from poetry.repositories.pypi_repository import PyPiRepository
    from tests.types import FixtureDirGetter


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


def test_isolated_env_install_with_constraints_success(pool: RepositoryPool) -> None:
    constraints = [
        Dependency("poetry-core", "<2", groups=[CONSTRAINTS_GROUP_NAME]),
        Dependency("attrs", ">1", groups=[CONSTRAINTS_GROUP_NAME]),
    ]

    with ephemeral_environment(Path(sys.executable)) as venv:
        env = IsolatedEnv(venv, pool)
        assert not InstalledRepository.load(venv).find_packages(
            get_dependency("poetry-core")
        )
        assert not InstalledRepository.load(venv).find_packages(get_dependency("attrs"))

        env.install({"poetry-core"}, constraints=constraints)
        assert InstalledRepository.load(venv).find_packages(
            get_dependency("poetry-core")
        )
        assert not InstalledRepository.load(venv).find_packages(get_dependency("attrs"))


def test_isolated_env_install_discards_requirements_not_needed_by_env(
    pool: RepositoryPool,
) -> None:
    with ephemeral_environment(Path(sys.executable)) as venv:
        env = IsolatedEnv(venv, pool)
        assert not InstalledRepository.load(venv).find_packages(
            get_dependency("poetry-core")
        )

        venv_python_version = venv.get_marker_env().get("python_version")
        package_one = uuid.uuid4().hex
        package_two = uuid.uuid4().hex

        env.install(
            {
                f"poetry-core; python_version=='{venv_python_version}'",
                f"{package_one}>=1.0.0; python_version=='0.0'",
                f"{package_two}>=2.0.0; platform_system=='Mirrors'",
            }
        )
        assert InstalledRepository.load(venv).find_packages(
            get_dependency("poetry-core")
        )
        assert not InstalledRepository.load(venv).find_packages(
            get_dependency(package_one)
        )

        assert not InstalledRepository.load(venv).find_packages(
            get_dependency(package_two)
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


@pytest.mark.parametrize(
    ("requirements", "constraints", "exception"),
    [
        (
            {"poetry-core==1.5.0"},
            [("poetry-core", "1.6.0")],
            IncompatibleConstraintsError,
        ),
        ({"black==19.10b0"}, [("attrs", "17.4.0")], SolverProblemError),
    ],
)
def test_isolated_env_install_with_constraints_error(
    requirements: Collection[str],
    constraints: list[tuple[str, str]],
    exception: type[Exception],
    pool: RepositoryPool,
) -> None:
    with ephemeral_environment(Path(sys.executable)) as venv:
        env = IsolatedEnv(venv, pool)
        with pytest.raises(exception):
            env.install(
                requirements,
                constraints=[
                    Dependency(name, version, groups=[CONSTRAINTS_GROUP_NAME])
                    for name, version in constraints
                ],
            )


def test_isolated_env_install_failure(
    pool: RepositoryPool, mocker: MockerFixture
) -> None:
    mocker.patch("poetry.installation.installer.Installer.run", return_value=1)
    with ephemeral_environment(Path(sys.executable)) as venv:
        env = IsolatedEnv(venv, pool)
        with pytest.raises(IsolatedBuildInstallError) as e:
            env.install({"a", "b>1"})
        assert e.value.requirements == {"a", "b>1"}


def test_isolated_builder_outside_poetry_project_context(
    tmp_working_directory: Path, fixture_dir: FixtureDirGetter
) -> None:
    source = tmp_working_directory / "source"
    shutil.copytree(fixture_dir("project_with_setup"), source)
    destination = tmp_working_directory / "dist"

    try:
        with isolated_builder(source, "wheel") as builder:
            builder.metadata_path(destination)
    except RuntimeError:
        pytest.fail("Isolated builder did not fallback to default repository pool")
