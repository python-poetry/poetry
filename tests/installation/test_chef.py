from __future__ import annotations

import shutil
import sys

from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile

import pytest

from build import ProjectBuilder
from build.__main__ import build_package
from packaging.tags import Tag
from poetry.core.packages.utils.link import Link
from pyproject_hooks import quiet_subprocess_runner

from poetry.factory import Factory
from poetry.installation.chef import Chef
from poetry.installation.chef import IsolatedEnv
from poetry.repositories import RepositoryPool
from poetry.utils.env import EnvManager
from poetry.utils.env import MockEnv
from poetry.utils.env import ephemeral_environment
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


@pytest.mark.parametrize(
    ("link", "cached"),
    [
        (
            "https://files.python-poetry.org/demo-0.1.0.tar.gz",
            "/cache/demo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
        ),
        (
            "https://example.com/demo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
            "/cache/demo-0.1.0-cp38-cp38-macosx_10_15_x86_64.whl",
        ),
    ],
)
def test_get_cached_archive_for_link(
    config: Config, mocker: MockerFixture, link: str, cached: str
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

    archive = chef.get_cached_archive_for_link(Link(link))

    assert Path(cached) == archive


def test_get_cached_archives_for_link(config: Config, mocker: MockerFixture):
    chef = Chef(
        config,
        MockEnv(
            marker_env={"interpreter_name": "cpython", "interpreter_version": "3.8.3"}
        ),
    )

    distributions = Path(__file__).parent.parent.joinpath("fixtures/distributions")
    mocker.patch.object(
        chef,
        "get_cache_directory_for_link",
        return_value=distributions,
    )

    archives = chef.get_cached_archives_for_link(
        Link("https://files.python-poetry.org/demo-0.1.0.tar.gz")
    )

    assert archives
    assert set(archives) == set(distributions.glob("demo-0.1.*"))


def test_get_cache_directory_for_link(config: Config, config_cache_dir: Path):
    chef = Chef(
        config,
        MockEnv(
            marker_env={"interpreter_name": "cpython", "interpreter_version": "3.8.3"}
        ),
    )

    directory = chef.get_cache_directory_for_link(
        Link("https://files.python-poetry.org/poetry-1.1.0.tar.gz")
    )

    expected = Path(
        f"{config_cache_dir.as_posix()}/artifacts/ba/63/13/"
        "283a3b3b7f95f05e9e6f84182d276f7bb0951d5b0cc24422b33f7a4648"
    )

    assert directory == expected


def test_prepare_sdist(config: Config, config_cache_dir: Path) -> None:
    chef = Chef(config, EnvManager.get_system_env())

    archive = (
        Path(__file__)
        .parent.parent.joinpath("fixtures/distributions/demo-0.1.0.tar.gz")
        .resolve()
    )

    destination = chef.get_cache_directory_for_link(Link(archive.as_uri()))

    wheel = chef.prepare(archive)

    assert wheel.parent == destination
    assert wheel.name == "demo-0.1.0-py3-none-any.whl"


def test_prepare_directory(config: Config, config_cache_dir: Path):
    chef = Chef(config, EnvManager.get_system_env())

    archive = Path(__file__).parent.parent.joinpath("fixtures/simple_project").resolve()

    wheel = chef.prepare(archive)

    assert wheel.name == "simple_project-1.2.3-py2.py3-none-any.whl"


def test_prepare_directory_with_extensions(
    config: Config, config_cache_dir: Path
) -> None:
    env = EnvManager.get_system_env()
    chef = Chef(config, env)

    archive = (
        Path(__file__)
        .parent.parent.joinpath("fixtures/extended_with_no_setup")
        .resolve()
    )

    wheel = chef.prepare(archive)

    assert wheel.name == f"extended-0.1-{env.supported_tags[0]}.whl"


def test_build(tmp_path: Path):
    archive = tmp_path / "extended_with_no_setup"

    # Copy `pep_517_backend` to a temporary directory as we need to dynamically add the
    # build system during the test. This ensures that we don't update the source, since
    # the value of `requires` is dynamic.
    shutil.copytree(
        Path(__file__)
        .parent.parent.joinpath("fixtures/extended_with_no_setup")
        .resolve(),
        archive,
    )

    build_package(
        srcdir=str(archive),
        outdir=str(archive),
        distributions=["wheel"],
    )
    distributions = list(archive.glob("extended-0.1-cp*-cp*-*.whl"))
    assert len(distributions) == 1
    whl = distributions[0]
    assert whl.stem.rsplit("-")[-1] == "dummy"


def test_build2(tmp_path: Path, config: Config):
    archive = tmp_path / "extended_with_no_setup"

    # Copy `pep_517_backend` to a temporary directory as we need to dynamically add the
    # build system during the test. This ensures that we don't update the source, since
    # the value of `requires` is dynamic.
    shutil.copytree(
        Path(__file__)
        .parent.parent.joinpath("fixtures/extended_with_no_setup")
        .resolve(),
        archive,
    )

    with ephemeral_environment(EnvManager.get_system_env().python) as venv:
        env = IsolatedEnv(venv, config)
        builder = ProjectBuilder(
            archive,
            python_executable=env.executable,
            scripts_dir=env.scripts_dir,
            runner=quiet_subprocess_runner,
        )
        env.install(builder.build_system_requires)

        env.install(
            builder.build_system_requires | builder.get_requires_for_build("wheel")
        )
        whl = Path(builder.build("wheel", archive.as_posix()))

    assert whl.stem.rsplit("-")[-1] == "dummy"


def test_build3(tmp_path: Path, config: Config):
    archive = tmp_path / "extended_with_no_setup"

    # Copy `pep_517_backend` to a temporary directory as we need to dynamically add the
    # build system during the test. This ensures that we don't update the source, since
    # the value of `requires` is dynamic.
    shutil.copytree(
        Path(__file__)
        .parent.parent.joinpath("fixtures/extended_with_no_setup")
        .resolve(),
        archive,
    )

    with ephemeral_environment(EnvManager.get_system_env().python) as venv:
        env = IsolatedEnv(venv, config)
        builder = ProjectBuilder(
            archive,
            python_executable=sys.executable,
            scripts_dir=env.scripts_dir,
            runner=quiet_subprocess_runner,
        )
        env.install(builder.build_system_requires)

        env.install(
            builder.build_system_requires | builder.get_requires_for_build("wheel")
        )
        whl = Path(builder.build("wheel", archive.as_posix()))

    assert whl.stem.rsplit("-")[-1] == "dummy"


def test_build4(tmp_path: Path, config: Config):
    archive = tmp_path / "extended_with_no_setup"

    # Copy `pep_517_backend` to a temporary directory as we need to dynamically add the
    # build system during the test. This ensures that we don't update the source, since
    # the value of `requires` is dynamic.
    shutil.copytree(
        Path(__file__)
        .parent.parent.joinpath("fixtures/extended_with_no_setup")
        .resolve(),
        archive,
    )

    with ephemeral_environment(EnvManager.get_system_env().python) as venv:
        env = IsolatedEnv(venv, config)
        builder = ProjectBuilder(archive)
        env.install(builder.build_system_requires)

        env.install(
            builder.build_system_requires | builder.get_requires_for_build("wheel")
        )
        whl = Path(builder.build("wheel", archive.as_posix()))

    assert whl.stem.rsplit("-")[-1] == "dummy"


def test_prepare_directory_editable(config: Config, config_cache_dir: Path):
    chef = Chef(config, EnvManager.get_system_env())

    archive = Path(__file__).parent.parent.joinpath("fixtures/simple_project").resolve()

    wheel = chef.prepare(archive, editable=True)

    assert wheel.name == "simple_project-1.2.3-py2.py3-none-any.whl"

    with ZipFile(wheel) as z:
        assert "simple_project.pth" in z.namelist()
