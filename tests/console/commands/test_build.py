from __future__ import annotations

import shutil
import tarfile

from typing import TYPE_CHECKING

import pytest

from poetry.factory import Factory


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.testers.command_tester import CommandTester

    from poetry.poetry import Poetry
    from poetry.utils.env import VirtualEnv
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter


@pytest.fixture
def tmp_project_path(tmp_path: Path) -> Path:
    return tmp_path / "project"


@pytest.fixture
def tmp_poetry(tmp_project_path: Path, fixture_dir: FixtureDirGetter) -> Poetry:
    # copy project so that we start with a clean directory
    shutil.copytree(fixture_dir("simple_project"), tmp_project_path)
    poetry = Factory().create_poetry(tmp_project_path)
    return poetry


@pytest.fixture
def tmp_tester(
    tmp_poetry: Poetry, command_tester_factory: CommandTesterFactory
) -> CommandTester:
    return command_tester_factory("build", tmp_poetry)


def get_package_glob(poetry: Poetry) -> str:
    return f"{poetry.package.name.replace('-', '_')}-{poetry.package.version}*"


def test_build_format_is_not_valid(tmp_tester: CommandTester) -> None:
    with pytest.raises(ValueError, match=r"Invalid format.*"):
        tmp_tester.execute("--format not_valid")


@pytest.mark.parametrize("format", ["sdist", "wheel", "all"])
def test_build_creates_packages_in_dist_directory_if_no_output_is_specified(
    tmp_tester: CommandTester, tmp_project_path: Path, tmp_poetry: Poetry, format: str
) -> None:
    tmp_tester.execute(f"--format {format}")
    build_artifacts = tuple(
        (tmp_project_path / "dist").glob(get_package_glob(tmp_poetry))
    )
    assert len(build_artifacts) > 0
    assert all(archive.exists() for archive in build_artifacts)


def test_build_not_possible_in_non_package_mode(
    fixture_dir: FixtureDirGetter,
    command_tester_factory: CommandTesterFactory,
) -> None:
    source_dir = fixture_dir("non_package_mode")

    poetry = Factory().create_poetry(source_dir)
    tester = command_tester_factory("build", poetry)

    assert tester.execute() == 1
    assert (
        tester.io.fetch_error()
        == "Building a package is not possible in non-package mode.\n"
    )


def test_build_with_multiple_readme_files(
    fixture_dir: FixtureDirGetter,
    tmp_path: Path,
    tmp_venv: VirtualEnv,
    command_tester_factory: CommandTesterFactory,
) -> None:
    source_dir = fixture_dir("with_multiple_readme_files")
    target_dir = tmp_path / "project"
    shutil.copytree(str(source_dir), str(target_dir))

    poetry = Factory().create_poetry(target_dir)
    tester = command_tester_factory("build", poetry, environment=tmp_venv)
    tester.execute()

    build_dir = target_dir / "dist"
    assert build_dir.exists()

    sdist_file = build_dir / "my_package-0.1.tar.gz"
    assert sdist_file.exists()
    assert sdist_file.stat().st_size > 0

    (wheel_file,) = build_dir.glob("my_package-0.1-*.whl")
    assert wheel_file.exists()
    assert wheel_file.stat().st_size > 0

    with tarfile.open(sdist_file) as tf:
        sdist_content = tf.getnames()

    assert "my_package-0.1/README-1.rst" in sdist_content
    assert "my_package-0.1/README-2.rst" in sdist_content


@pytest.mark.parametrize(
    "output_dir", [None, "dist", "test/dir", "../dist", "absolute"]
)
def test_build_output_option(
    tmp_tester: CommandTester,
    tmp_project_path: Path,
    tmp_poetry: Poetry,
    output_dir: str,
) -> None:
    if output_dir is None:
        tmp_tester.execute()
        build_dir = tmp_project_path / "dist"
    elif output_dir == "absolute":
        tmp_tester.execute(f"--output {tmp_project_path / 'tmp/dist'}")
        build_dir = tmp_project_path / "tmp/dist"
    else:
        tmp_tester.execute(f"--output {output_dir}")
        build_dir = tmp_project_path / output_dir

    build_artifacts = tuple(build_dir.glob(get_package_glob(tmp_poetry)))
    assert len(build_artifacts) > 0
    assert all(archive.exists() for archive in build_artifacts)
