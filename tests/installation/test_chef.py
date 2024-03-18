from __future__ import annotations

import os
import shutil
import tempfile

from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile

import pytest

from build import ProjectBuilder
from poetry.core.packages.utils.link import Link

from poetry.factory import Factory
from poetry.installation.chef import Chef
from poetry.repositories import RepositoryPool
from poetry.utils.env import EnvManager


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from poetry.repositories.pypi_repository import PyPiRepository
    from poetry.utils.cache import ArtifactCache
    from tests.conftest import Config
    from tests.types import FixtureDirGetter


@pytest.fixture()
def pool(pypi_repository: PyPiRepository) -> RepositoryPool:
    pool = RepositoryPool()

    pool.add_repository(pypi_repository)

    return pool


@pytest.fixture(autouse=True)
def setup(mocker: MockerFixture, pool: RepositoryPool) -> None:
    mocker.patch.object(Factory, "create_pool", return_value=pool)


def test_prepare_sdist(
    config: Config,
    config_cache_dir: Path,
    artifact_cache: ArtifactCache,
    fixture_dir: FixtureDirGetter,
) -> None:
    chef = Chef(
        artifact_cache, EnvManager.get_system_env(), Factory.create_pool(config)
    )
    archive = (fixture_dir("distributions") / "demo-0.1.0.tar.gz").resolve()
    destination = artifact_cache.get_cache_directory_for_link(Link(archive.as_uri()))

    wheel = chef.prepare(archive)

    assert wheel.parent == destination
    assert wheel.name == "demo-0.1.0-py3-none-any.whl"


def test_prepare_directory(
    config: Config,
    config_cache_dir: Path,
    artifact_cache: ArtifactCache,
    fixture_dir: FixtureDirGetter,
) -> None:
    chef = Chef(
        artifact_cache, EnvManager.get_system_env(), Factory.create_pool(config)
    )
    archive = fixture_dir("simple_project").resolve()

    wheel = chef.prepare(archive)

    assert wheel.name == "simple_project-1.2.3-py2.py3-none-any.whl"

    assert wheel.parent.parent == Path(tempfile.gettempdir())
    # cleanup generated tmp dir artifact
    os.unlink(wheel)


@pytest.mark.network
def test_prepare_directory_with_extensions(
    config: Config,
    config_cache_dir: Path,
    artifact_cache: ArtifactCache,
    fixture_dir: FixtureDirGetter,
    tmp_path: Path,
) -> None:
    env = EnvManager.get_system_env()
    chef = Chef(artifact_cache, env, Factory.create_pool(config))
    archive = shutil.copytree(
        fixture_dir("extended_with_no_setup").resolve(), tmp_path / "project"
    )

    wheel = chef.prepare(archive)

    assert wheel.parent.parent == Path(tempfile.gettempdir())
    assert wheel.name == f"extended-0.1-{env.supported_tags[0]}.whl"

    # cleanup generated tmp dir artifact
    os.unlink(wheel)


def test_prepare_directory_editable(
    config: Config,
    config_cache_dir: Path,
    artifact_cache: ArtifactCache,
    fixture_dir: FixtureDirGetter,
) -> None:
    chef = Chef(
        artifact_cache, EnvManager.get_system_env(), Factory.create_pool(config)
    )
    archive = fixture_dir("simple_project").resolve()

    wheel = chef.prepare(archive, editable=True)

    assert wheel.parent.parent == Path(tempfile.gettempdir())
    assert wheel.name == "simple_project-1.2.3-py2.py3-none-any.whl"

    with ZipFile(wheel) as z:
        assert "simple_project.pth" in z.namelist()

    # cleanup generated tmp dir artifact
    os.unlink(wheel)


@pytest.mark.network
def test_prepare_directory_script(
    config: Config,
    config_cache_dir: Path,
    artifact_cache: ArtifactCache,
    fixture_dir: FixtureDirGetter,
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    """
    Building a project that requires calling a script from its build_requires.
    """
    # make sure the scripts project is on the same drive (for Windows tests in CI)
    scripts_dir = tmp_path / "scripts"
    shutil.copytree(fixture_dir("scripts"), scripts_dir)

    orig_build_system_requires = ProjectBuilder.build_system_requires

    class CustomPropertyMock:
        def __get__(
            self, obj: ProjectBuilder, obj_type: type[ProjectBuilder] | None = None
        ) -> set[str]:
            assert isinstance(obj, ProjectBuilder)
            return {
                req.replace("<scripts>", f"scripts @ {scripts_dir.as_uri()}")
                for req in orig_build_system_requires.fget(obj)  # type: ignore[attr-defined]
            }

    mocker.patch(
        "build.ProjectBuilder.build_system_requires",
        new_callable=CustomPropertyMock,
    )
    chef = Chef(
        artifact_cache, EnvManager.get_system_env(), Factory.create_pool(config)
    )
    archive = shutil.copytree(
        fixture_dir("project_with_setup_calls_script").resolve(), tmp_path / "project"
    )
    wheel = chef.prepare(archive)

    assert wheel.name == "project_with_setup_calls_script-0.1.2-py3-none-any.whl"

    assert wheel.parent.parent == Path(tempfile.gettempdir())
    # cleanup generated tmp dir artifact
    os.unlink(wheel)
