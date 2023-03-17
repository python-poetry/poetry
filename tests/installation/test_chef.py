from __future__ import annotations

import os
import shutil
import tempfile

from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile

import pytest

from packaging.tags import Tag
from poetry.core.packages.utils.link import Link

from poetry.factory import Factory
from poetry.installation.chef import Chef
from poetry.repositories import RepositoryPool
from poetry.utils.env import EnvManager
from poetry.utils.env import MockEnv
from tests.repositories.test_pypi_repository import MockRepository


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tests.conftest import Config
    from tests.types import FixtureDirGetter


@pytest.fixture()
def pool() -> RepositoryPool:
    pool = RepositoryPool()

    pool.add_repository(MockRepository())

    return pool


@pytest.fixture(autouse=True)
def setup(mocker: MockerFixture, pool: RepositoryPool) -> None:
    mocker.patch.object(Factory, "create_pool", return_value=pool)


@pytest.mark.parametrize(
    ("link", "strict", "available_packages"),
    [
        (
            "https://files.python-poetry.org/demo-0.1.0.tar.gz",
            True,
            [
                Path("/cache/demo-0.1.0-py2.py3-none-any"),
                Path("/cache/demo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl"),
                Path("/cache/demo-0.1.0-cp37-cp37-macosx_10_15_x86_64.whl"),
            ],
        ),
        (
            "https://example.com/demo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            False,
            [],
        ),
    ],
)
def test_get_not_found_cached_archive_for_link(
    config: Config,
    mocker: MockerFixture,
    link: str,
    strict: bool,
    available_packages: list[Path],
):
    chef = Chef(
        config,
        MockEnv(
            version_info=(3, 8, 3),
            marker_env={"interpreter_name": "cpython", "interpreter_version": "3.8.3"},
            supported_tags=[
                Tag("cp38", "cp38", "macosx_10_15_x86_64"),
                Tag("py3", "none", "any"),
            ],
        ),
        Factory.create_pool(config),
    )

    mocker.patch.object(
        chef, "get_cached_archives_for_link", return_value=available_packages
    )

    archive = chef.get_cached_archive_for_link(Link(link), strict=strict)

    assert archive is None


@pytest.mark.parametrize(
    ("link", "cached", "strict"),
    [
        (
            "https://files.python-poetry.org/demo-0.1.0.tar.gz",
            "/cache/demo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            False,
        ),
        (
            "https://example.com/demo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            "/cache/demo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            False,
        ),
        (
            "https://files.python-poetry.org/demo-0.1.0.tar.gz",
            "/cache/demo-0.1.0.tar.gz",
            True,
        ),
        (
            "https://example.com/demo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            "/cache/demo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            True,
        ),
    ],
)
def test_get_found_cached_archive_for_link(
    config: Config, mocker: MockerFixture, link: str, cached: str, strict: bool
):
    chef = Chef(
        config,
        MockEnv(
            version_info=(3, 8, 3),
            marker_env={"interpreter_name": "cpython", "interpreter_version": "3.8.3"},
            supported_tags=[
                Tag("cp38", "cp38", "macosx_10_15_x86_64"),
                Tag("py3", "none", "any"),
            ],
        ),
        Factory.create_pool(config),
    )

    mocker.patch.object(
        chef,
        "get_cached_archives_for_link",
        return_value=[
            Path("/cache/demo-0.1.0-py2.py3-none-any"),
            Path("/cache/demo-0.1.0.tar.gz"),
            Path("/cache/demo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl"),
            Path("/cache/demo-0.1.0-cp37-cp37-macosx_10_15_x86_64.whl"),
        ],
    )

    archive = chef.get_cached_archive_for_link(Link(link), strict=strict)

    assert Path(cached) == archive


def test_get_cached_archives_for_link(
    config: Config, mocker: MockerFixture, fixture_dir: FixtureDirGetter, tmp_path: Path
) -> None:
    chef = Chef(
        config,
        MockEnv(
            marker_env={"interpreter_name": "cpython", "interpreter_version": "3.8.3"}
        ),
        Factory.create_pool(config),
    )

    for file in fixture_dir("distributions").glob("demo-0.1.*"):
        shutil.copy(file, tmp_path)
    (Path(tmp_path) / "no-distribution-by-suffix.txt").touch()
    mocker.patch.object(
        chef,
        "get_cache_directory_for_link",
        return_value=tmp_path,
    )

    archives = chef.get_cached_archives_for_link(
        Link("https://files.python-poetry.org/demo-0.1.0.tar.gz")
    )

    assert archives
    assert set(archives) == set(tmp_path.glob("demo-0.1.*"))


def test_get_cache_directory_for_link(config: Config, config_cache_dir: Path):
    chef = Chef(
        config,
        MockEnv(
            marker_env={"interpreter_name": "cpython", "interpreter_version": "3.8.3"}
        ),
        Factory.create_pool(config),
    )

    directory = chef.get_cache_directory_for_link(
        Link("https://files.python-poetry.org/poetry-1.1.0.tar.gz")
    )

    expected = Path(
        f"{config_cache_dir.as_posix()}/artifacts/ba/63/13/"
        "283a3b3b7f95f05e9e6f84182d276f7bb0951d5b0cc24422b33f7a4648"
    )

    assert directory == expected


def test_prepare_sdist(
    config: Config, config_cache_dir: Path, fixture_dir: FixtureDirGetter
) -> None:
    chef = Chef(config, EnvManager.get_system_env(), Factory.create_pool(config))

    archive = fixture_dir("distributions/demo-0.1.0.tar.gz").resolve()

    destination = chef.get_cache_directory_for_link(Link(archive.as_uri()))

    wheel = chef.prepare(archive)

    assert wheel.parent == destination
    assert wheel.name == "demo-0.1.0-py3-none-any.whl"


def test_prepare_directory(
    config: Config, config_cache_dir: Path, fixture_dir: FixtureDirGetter
) -> None:
    chef = Chef(config, EnvManager.get_system_env(), Factory.create_pool(config))

    archive = fixture_dir("simple_project").resolve()

    wheel = chef.prepare(archive)

    assert wheel.name == "simple_project-1.2.3-py2.py3-none-any.whl"

    assert wheel.parent.parent == Path(tempfile.gettempdir())
    # cleanup generated tmp dir artifact
    os.unlink(wheel)


def test_prepare_directory_with_extensions(
    config: Config, config_cache_dir: Path, fixture_dir: FixtureDirGetter
) -> None:
    env = EnvManager.get_system_env()
    chef = Chef(config, env, Factory.create_pool(config))

    archive = fixture_dir("extended_with_no_setup").resolve()

    wheel = chef.prepare(archive)

    assert wheel.parent.parent == Path(tempfile.gettempdir())
    assert wheel.name == f"extended-0.1-{env.supported_tags[0]}.whl"

    # cleanup generated tmp dir artifact
    os.unlink(wheel)


def test_prepare_directory_editable(
    config: Config, config_cache_dir: Path, fixture_dir: FixtureDirGetter
) -> None:
    chef = Chef(config, EnvManager.get_system_env(), Factory.create_pool(config))

    archive = fixture_dir("simple_project").resolve()

    wheel = chef.prepare(archive, editable=True)

    assert wheel.parent.parent == Path(tempfile.gettempdir())
    assert wheel.name == "simple_project-1.2.3-py2.py3-none-any.whl"

    with ZipFile(wheel) as z:
        assert "simple_project.pth" in z.namelist()

    # cleanup generated tmp dir artifact
    os.unlink(wheel)
