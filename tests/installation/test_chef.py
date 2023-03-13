from __future__ import annotations

import os
import tempfile

from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile

import pytest

from poetry.core.packages.utils.link import Link

from poetry.factory import Factory
from poetry.installation.chef import Chef
from poetry.repositories import RepositoryPool
from poetry.utils.cache import ArtifactCache
from poetry.utils.env import EnvManager
from tests.repositories.test_pypi_repository import MockRepository


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tests.conftest import Config


@pytest.fixture()
def pool() -> RepositoryPool:
    pool = RepositoryPool()

    pool.add_repository(MockRepository())

    return pool


@pytest.fixture(autouse=True)
def setup(mocker: MockerFixture, pool: RepositoryPool) -> None:
    mocker.patch.object(Factory, "create_pool", return_value=pool)


@pytest.fixture()
def artifact_cache(config: Config) -> ArtifactCache:
    return ArtifactCache(cache_dir=config.artifacts_cache_directory)


def test_prepare_sdist(
    config: Config, config_cache_dir: Path, artifact_cache: ArtifactCache
) -> None:
    chef = Chef(
        artifact_cache, EnvManager.get_system_env(), Factory.create_pool(config)
    )

    archive = (
        Path(__file__)
        .parent.parent.joinpath("fixtures/distributions/demo-0.1.0.tar.gz")
        .resolve()
    )

    destination = artifact_cache.get_cache_directory_for_link(Link(archive.as_uri()))

    wheel = chef.prepare(archive)

    assert wheel.parent == destination
    assert wheel.name == "demo-0.1.0-py3-none-any.whl"


def test_prepare_directory(
    config: Config, config_cache_dir: Path, artifact_cache: ArtifactCache
):
    chef = Chef(
        artifact_cache, EnvManager.get_system_env(), Factory.create_pool(config)
    )

    archive = Path(__file__).parent.parent.joinpath("fixtures/simple_project").resolve()

    wheel = chef.prepare(archive)

    assert wheel.name == "simple_project-1.2.3-py2.py3-none-any.whl"

    assert wheel.parent.parent == Path(tempfile.gettempdir())
    # cleanup generated tmp dir artifact
    os.unlink(wheel)


def test_prepare_directory_with_extensions(
    config: Config, config_cache_dir: Path, artifact_cache: ArtifactCache
) -> None:
    env = EnvManager.get_system_env()
    chef = Chef(artifact_cache, env, Factory.create_pool(config))

    archive = (
        Path(__file__)
        .parent.parent.joinpath("fixtures/extended_with_no_setup")
        .resolve()
    )

    wheel = chef.prepare(archive)

    assert wheel.parent.parent == Path(tempfile.gettempdir())
    assert wheel.name == f"extended-0.1-{env.supported_tags[0]}.whl"

    # cleanup generated tmp dir artifact
    os.unlink(wheel)


def test_prepare_directory_editable(
    config: Config, config_cache_dir: Path, artifact_cache: ArtifactCache
):
    chef = Chef(
        artifact_cache, EnvManager.get_system_env(), Factory.create_pool(config)
    )

    archive = Path(__file__).parent.parent.joinpath("fixtures/simple_project").resolve()

    wheel = chef.prepare(archive, editable=True)

    assert wheel.parent.parent == Path(tempfile.gettempdir())
    assert wheel.name == "simple_project-1.2.3-py2.py3-none-any.whl"

    with ZipFile(wheel) as z:
        assert "simple_project.pth" in z.namelist()

    # cleanup generated tmp dir artifact
    os.unlink(wheel)
