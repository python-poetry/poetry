from __future__ import annotations

import os
import shutil
import sys
import tempfile

from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile

import pytest

from build import ProjectBuilder
from packaging.utils import parse_wheel_filename
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


@pytest.mark.parametrize("build_fails", [False, True])
def test_prepare_sdist_publishes_only_completed_wheels(
    build_fails: bool,
    artifact_cache: ArtifactCache,
    fixture_dir: FixtureDirGetter,
    mocker: MockerFixture,
    pool: RepositoryPool,
    tmp_path: Path,
) -> None:
    chef = Chef(artifact_cache, EnvManager.get_system_env(), pool)
    archive = (fixture_dir("distributions") / "demo-0.1.0.tar.gz").resolve()
    destination = tmp_path / "cache"
    cached_wheel = destination / "demo-0.1.0-py3-none-any.whl"
    observed = []

    def build_wheel(source: Path, output: Path, **kwargs: object) -> Path:
        wheel = output / cached_wheel.name
        wheel.write_bytes(b"unfinished wheel")
        observed.append(cached_wheel.exists())
        if build_fails:
            raise RuntimeError("backend failed")
        with ZipFile(wheel, "w") as complete:
            complete.writestr("demo.py", "pass")
        return wheel

    mocker.patch.object(chef, "_prepare", side_effect=build_wheel)
    if build_fails:
        with pytest.raises(RuntimeError, match="backend failed"):
            chef.prepare(archive, output_dir=destination)
        assert not list(destination.iterdir())
    else:
        assert chef.prepare(archive, output_dir=destination) == cached_wheel
        with ZipFile(cached_wheel) as complete:
            assert complete.read("demo.py") == b"pass"
        assert list(destination.iterdir()) == [cached_wheel]
    assert observed == [False]


@pytest.mark.skipif(
    sys.platform != "win32", reason="Windows blocks replacing open files"
)
def test_prepare_sdist_keeps_completed_wheel_in_use(
    artifact_cache: ArtifactCache,
    fixture_dir: FixtureDirGetter,
    mocker: MockerFixture,
    pool: RepositoryPool,
    tmp_path: Path,
) -> None:
    chef = Chef(artifact_cache, EnvManager.get_system_env(), pool)
    destination = tmp_path / "cache"
    destination.mkdir()
    archive = destination / "demo-0.1.0.tar.gz"
    shutil.copyfile(fixture_dir("distributions") / archive.name, archive)
    cached_wheel = destination / "demo-0.1.0-py3-none-any.whl"
    with ZipFile(cached_wheel, "w") as cached:
        cached.writestr("demo.py", "cached")

    def build_wheel(source: Path, output: Path, **kwargs: object) -> Path:
        wheel = output / cached_wheel.name
        with ZipFile(wheel, "w") as complete:
            complete.writestr("demo.py", "new")
        return wheel

    mocker.patch.object(chef, "_prepare", side_effect=build_wheel)
    with ZipFile(cached_wheel) as reader:
        assert chef.prepare(archive, output_dir=destination) == cached_wheel
        assert reader.read("demo.py") == b"cached"
    assert set(destination.iterdir()) == {archive, cached_wheel}


def test_prepare_directory(
    config: Config,
    config_cache_dir: Path,
    artifact_cache: ArtifactCache,
    fixture_dir: FixtureDirGetter,
) -> None:
    chef = Chef(
        artifact_cache, EnvManager.get_system_env(), Factory.create_pool(config)
    )
    archive = fixture_dir("simple_project_legacy").resolve()

    wheel = chef.prepare(archive)

    assert wheel.name == "simple_project-1.2.3-py2.py3-none-any.whl"

    assert wheel.parent.parent == Path(tempfile.gettempdir())
    # cleanup generated tmp dir artifact
    os.unlink(wheel)


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
    name, version, _, tags = parse_wheel_filename(wheel.name)
    assert name == "extended"
    assert str(version) == "0.1"
    assert not tags.isdisjoint(env.supported_tags)

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
    archive = fixture_dir("simple_project_legacy").resolve()

    wheel = chef.prepare(archive, editable=True)

    assert wheel.parent.parent == Path(tempfile.gettempdir())
    assert wheel.name == "simple_project-1.2.3-py2.py3-none-any.whl"

    with ZipFile(wheel) as z:
        assert "simple_project.pth" in z.namelist()

    # cleanup generated tmp dir artifact
    os.unlink(wheel)


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
