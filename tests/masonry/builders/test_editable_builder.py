from __future__ import annotations

import csv
import json
import os
import shutil

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cleo.io.null_io import NullIO
from deepdiff.diff import DeepDiff
from poetry.core.constraints.version import Version
from poetry.core.masonry.metadata import Metadata
from poetry.core.packages.package import Package

from poetry.factory import Factory
from poetry.masonry.builders.editable import EditableBuilder
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils._compat import getencoding
from poetry.utils.env import EnvCommandError
from poetry.utils.env import EnvManager
from poetry.utils.env import MockEnv
from poetry.utils.env import VirtualEnv
from poetry.utils.env import ephemeral_environment


if TYPE_CHECKING:
    from collections.abc import Iterator

    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.types import FixtureDirGetter


@pytest.fixture()
def simple_poetry(fixture_dir: FixtureDirGetter) -> Poetry:
    poetry = Factory().create_poetry(fixture_dir("simple_project"))

    return poetry


@pytest.fixture()
def project_with_include(fixture_dir: FixtureDirGetter) -> Poetry:
    poetry = Factory().create_poetry(fixture_dir("with-include"))

    return poetry


@pytest.fixture()
def extended_poetry(fixture_dir: FixtureDirGetter) -> Poetry:
    poetry = Factory().create_poetry(fixture_dir("extended_project"))

    return poetry


@pytest.fixture()
def extended_without_setup_poetry(fixture_dir: FixtureDirGetter) -> Poetry:
    poetry = Factory().create_poetry(fixture_dir("extended_project_without_setup"))

    return poetry


@pytest.fixture
def with_multiple_readme_files(fixture_dir: FixtureDirGetter) -> Poetry:
    poetry = Factory().create_poetry(fixture_dir("with_multiple_readme_files"))

    return poetry


@pytest.fixture()
def env_manager(simple_poetry: Poetry) -> EnvManager:
    return EnvManager(simple_poetry)


@pytest.fixture
def tmp_venv(tmp_path: Path, env_manager: EnvManager) -> Iterator[VirtualEnv]:
    venv_path = tmp_path / "venv"

    env_manager.build_venv(venv_path)

    venv = VirtualEnv(venv_path)
    yield venv

    shutil.rmtree(str(venv.path))


@pytest.fixture()
def bad_scripts_no_colon(fixture_dir: FixtureDirGetter) -> Poetry:
    poetry = Factory().create_poetry(fixture_dir("bad_scripts_project/no_colon"))

    return poetry


@pytest.fixture()
def bad_scripts_too_many_colon(fixture_dir: FixtureDirGetter) -> Poetry:
    poetry = Factory().create_poetry(fixture_dir("bad_scripts_project/too_many_colon"))

    return poetry


def expected_metadata_version() -> str:
    # Get the metadata version that we should expect: which is poetry-core's default
    # value.
    metadata = Metadata()
    return metadata.metadata_version


def expected_python_classifiers(min_version: str | None = None) -> str:
    if min_version:
        min_version_tuple = tuple(map(int, min_version.split(".")))
        relevant_versions = set()
        for version in Package.AVAILABLE_PYTHONS:
            version_tuple = tuple(map(int, version.split(".")))
            if version_tuple >= min_version_tuple[: len(version_tuple)]:
                relevant_versions.add(version)
    else:
        relevant_versions = Package.AVAILABLE_PYTHONS
    return "\n".join(
        f"Classifier: Programming Language :: Python :: {version}"
        for version in sorted(
            relevant_versions, key=lambda x: tuple(map(int, x.split(".")))
        )
    )


@pytest.mark.parametrize("project", ("simple_project", "simple_project_legacy"))
def test_builder_installs_proper_files_for_standard_packages(
    project: str,
    simple_poetry: Poetry,
    tmp_path: Path,
    fixture_dir: FixtureDirGetter,
) -> None:
    simple_poetry = Factory().create_poetry(fixture_dir(project))
    env_manager = EnvManager(simple_poetry)
    venv_path = tmp_path / "venv"
    env_manager.build_venv(venv_path)
    tmp_venv = VirtualEnv(venv_path)

    builder = EditableBuilder(simple_poetry, tmp_venv, NullIO())

    builder.build()

    assert tmp_venv._bin_dir.joinpath("foo").exists()
    pth_file = Path("simple_project.pth")
    assert tmp_venv.site_packages.exists(pth_file)
    assert (
        simple_poetry.file.path.parent.resolve().as_posix()
        == tmp_venv.site_packages.find(pth_file)[0]
        .read_text(encoding="utf-8")
        .strip(os.linesep)
    )

    dist_info = Path("simple_project-1.2.3.dist-info")
    assert tmp_venv.site_packages.exists(dist_info)

    dist_info = tmp_venv.site_packages.find(dist_info)[0]

    assert dist_info.joinpath("entry_points.txt").exists()
    assert dist_info.joinpath("WHEEL").exists()
    assert dist_info.joinpath("METADATA").exists()
    assert dist_info.joinpath("licenses/LICENSE").exists()
    assert dist_info.joinpath("INSTALLER").exists()
    assert dist_info.joinpath("RECORD").exists()
    assert dist_info.joinpath("direct_url.json").exists()

    assert not DeepDiff(
        {
            "dir_info": {"editable": True},
            "url": simple_poetry.file.path.parent.as_uri(),
        },
        json.loads(dist_info.joinpath("direct_url.json").read_text(encoding="utf-8")),
    )

    assert dist_info.joinpath("INSTALLER").read_text(encoding="utf-8") == "poetry"
    assert (
        dist_info.joinpath("entry_points.txt").read_text(encoding="utf-8")
        == "[console_scripts]\nbaz=bar:baz.boom.bim\nfoo=foo:bar\n"
        "fox=fuz.foo:bar.baz\n\n"
    )
    metadata = f"""\
Metadata-Version: {expected_metadata_version()}
Name: simple-project
Version: 1.2.3
Summary: Some description.
License: MIT
License-File: LICENSE
Keywords: packaging,dependency,poetry
Author: Sébastien Eustace
Author-email: sebastien@eustace.io
Requires-Python: >=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*
Classifier: License :: OSI Approved :: MIT License
{expected_python_classifiers()}
Classifier: Topic :: Software Development :: Build Tools
Classifier: Topic :: Software Development :: Libraries :: Python Modules
Project-URL: Documentation, https://python-poetry.org/docs
Project-URL: Homepage, https://python-poetry.org
Project-URL: Repository, https://github.com/python-poetry/poetry
Description-Content-Type: text/x-rst

My Package
==========

"""
    if project == "simple_project":
        metadata = metadata.replace("License:", "License-Expression:").replace(
            "Classifier: License :: OSI Approved :: MIT License\n", ""
        )
    assert dist_info.joinpath("METADATA").read_text(encoding="utf-8") == metadata

    with open(dist_info.joinpath("RECORD"), encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        records = list(reader)

    assert all(len(row) == 3 for row in records)
    record_entries = {row[0] for row in records}
    pth_file = Path("simple_project.pth")
    assert tmp_venv.site_packages.exists(pth_file)
    assert str(tmp_venv.site_packages.find(pth_file)[0]) in record_entries
    assert str(tmp_venv._bin_dir.joinpath("foo")) in record_entries
    assert str(tmp_venv._bin_dir.joinpath("baz")) in record_entries
    assert str(dist_info.joinpath("entry_points.txt")) in record_entries
    assert str(dist_info.joinpath("WHEEL")) in record_entries
    assert str(dist_info.joinpath("METADATA")) in record_entries
    assert str(dist_info.joinpath("licenses/LICENSE")) in record_entries

    assert str(dist_info.joinpath("INSTALLER")) in record_entries
    assert str(dist_info.joinpath("RECORD")) in record_entries
    assert str(dist_info.joinpath("direct_url.json")) in record_entries

    baz_script = f"""\
#!{tmp_venv.python}
import sys
from bar import baz

if __name__ == '__main__':
    sys.exit(baz.boom.bim())
"""

    assert tmp_venv._bin_dir.joinpath("baz").read_text(encoding="utf-8") == baz_script

    foo_script = f"""\
#!{tmp_venv.python}
import sys
from foo import bar

if __name__ == '__main__':
    sys.exit(bar())
"""

    assert tmp_venv._bin_dir.joinpath("foo").read_text(encoding="utf-8") == foo_script

    fox_script = f"""\
#!{tmp_venv.python}
import sys
from fuz.foo import bar

if __name__ == '__main__':
    sys.exit(bar.baz())
"""

    assert tmp_venv._bin_dir.joinpath("fox").read_text(encoding="utf-8") == fox_script


def test_builder_falls_back_on_setup_and_pip_for_packages_with_build_scripts(
    mocker: MockerFixture, extended_poetry: Poetry, tmp_path: Path
) -> None:
    pip_install = mocker.patch("poetry.masonry.builders.editable.pip_install")
    env = MockEnv(path=tmp_path / "foo")
    builder = EditableBuilder(extended_poetry, env, NullIO())

    builder.build()
    pip_install.assert_called_once_with(
        extended_poetry.pyproject.file.path.parent, env, upgrade=True, editable=True
    )
    assert env.executed == []


@pytest.mark.network
def test_builder_setup_generation_runs_with_pip_editable(
    fixture_dir: FixtureDirGetter, tmp_path: Path
) -> None:
    # create an isolated copy of the project
    fixture = fixture_dir("extended_project")
    extended_project = tmp_path / "extended_project"

    shutil.copytree(fixture, extended_project)
    assert extended_project.exists()

    poetry = Factory().create_poetry(extended_project)

    # we need a venv with pip and setuptools since we are verifying setup.py builds
    with ephemeral_environment(flags={"no-pip": False}) as venv:
        builder = EditableBuilder(poetry, venv, NullIO())
        builder.build()

        # is the package installed?
        repository = InstalledRepository.load(venv)
        package = repository.package("extended-project", Version.parse("1.2.3"))
        assert package.name == "extended-project"

        # check for the module built by build.py
        try:
            output = venv.run_python_script(
                "from extended_project import built; print(built.__file__)"
            ).strip()
        except EnvCommandError:
            pytest.fail("Unable to import built module")
        else:
            built_py = Path(output).resolve()

        expected = extended_project / "extended_project" / "built.py"

        # ensure the package was installed as editable
        assert built_py == expected.resolve()


def test_builder_installs_proper_files_when_packages_configured(
    project_with_include: Poetry, tmp_venv: VirtualEnv
) -> None:
    builder = EditableBuilder(project_with_include, tmp_venv, NullIO())
    builder.build()

    pth_file = Path("with_include.pth")
    assert tmp_venv.site_packages.exists(pth_file)

    pth_file = tmp_venv.site_packages.find(pth_file)[0]

    paths = set()
    with pth_file.open(encoding=getencoding()) as f:
        for line in f.readlines():
            line = line.strip(os.linesep)
            if line:
                paths.add(line)

    project_root = project_with_include.file.path.parent.resolve()
    expected = {project_root.as_posix(), project_root.joinpath("src").as_posix()}

    assert paths.issubset(expected)
    assert len(paths) == len(expected)


def test_builder_generates_proper_metadata_when_multiple_readme_files(
    with_multiple_readme_files: Poetry, tmp_venv: VirtualEnv
) -> None:
    builder = EditableBuilder(with_multiple_readme_files, tmp_venv, NullIO())

    builder.build()

    dist_info = Path("my_package-0.1.dist-info")
    assert tmp_venv.site_packages.exists(dist_info)

    dist_info = tmp_venv.site_packages.find(dist_info)[0]
    assert dist_info.joinpath("METADATA").exists()

    metadata = f"""\
Metadata-Version: {expected_metadata_version()}
Name: my-package
Version: 0.1
Summary: Some description.
License: MIT
Author: Your Name
Author-email: you@example.com
Requires-Python: >=3.7,<4.0
Classifier: License :: OSI Approved :: MIT License
{expected_python_classifiers("3.7")}
Project-URL: Homepage, https://python-poetry.org
Description-Content-Type: text/x-rst

Single Python
=============

Changelog
=========

"""
    assert dist_info.joinpath("METADATA").read_text(encoding="utf-8") == metadata


def test_builder_should_execute_build_scripts(
    mocker: MockerFixture, extended_without_setup_poetry: Poetry, tmp_path: Path
) -> None:
    env = MockEnv(path=tmp_path / "foo")
    mocker.patch(
        "poetry.masonry.builders.editable.build_environment"
    ).return_value.__enter__.return_value = env

    builder = EditableBuilder(extended_without_setup_poetry, env, NullIO())

    builder.build()

    assert [
        ["python", str(extended_without_setup_poetry.file.path.parent / "build.py")]
    ] == env.executed


def test_builder_catches_bad_scripts_no_colon(
    bad_scripts_no_colon: Poetry, tmp_venv: VirtualEnv
) -> None:
    builder = EditableBuilder(bad_scripts_no_colon, tmp_venv, NullIO())
    with pytest.raises(ValueError, match=r"Bad script.*") as e:
        builder.build()
    msg = str(e.value)
    # We should print out the problematic script entry
    assert "bar.bin.foo" in msg
    # and some hint about what to do
    assert "Hint:" in msg
    assert 'foo = "bar.bin.foo:main"' in msg


def test_builder_catches_bad_scripts_too_many_colon(
    bad_scripts_too_many_colon: Poetry, tmp_venv: VirtualEnv
) -> None:
    builder = EditableBuilder(bad_scripts_too_many_colon, tmp_venv, NullIO())
    with pytest.raises(ValueError, match=r"Bad script.*") as e:
        builder.build()
    msg = str(e.value)
    # We should print out the problematic script entry
    assert "foo::bar" in msg
    # and some hint about what is wrong
    assert "Too many" in msg


@pytest.fixture()
def file_scripts_poetry(fixture_dir: FixtureDirGetter) -> Poetry:
    poetry = Factory().create_poetry(fixture_dir("file_scripts_project"))
    return poetry


def test_builder_installs_file_scripts(
    file_scripts_poetry: Poetry,
    tmp_path: Path,
) -> None:
    env_manager = EnvManager(file_scripts_poetry)
    venv_path = tmp_path / "venv"
    env_manager.build_venv(venv_path)
    tmp_venv = VirtualEnv(venv_path)

    builder = EditableBuilder(file_scripts_poetry, tmp_venv, NullIO())
    builder.build()

    # The file script should be copied to the venv bin directory
    script_path = tmp_venv._bin_dir.joinpath("my-script")
    assert script_path.exists(), (
        f"File script 'my-script' was not copied to {tmp_venv._bin_dir}"
    )

    # Check script content matches the source
    source_content = (
        file_scripts_poetry.file.path.parent / "bin" / "my-script.sh"
    ).read_text(encoding="utf-8")
    assert script_path.read_text(encoding="utf-8") == source_content

    # Check the file is executable
    assert os.access(script_path, os.X_OK)

    # The console entry point should also be installed
    console_script = tmp_venv._bin_dir.joinpath("console-entry")
    assert console_script.exists(), (
        f"Console script 'console-entry' was not installed to {tmp_venv._bin_dir}"
    )


def test_builder_skips_missing_file_script(
    fixture_dir: FixtureDirGetter,
    tmp_path: Path,
) -> None:
    from cleo.io.buffered_io import BufferedIO

    poetry = Factory().create_poetry(fixture_dir("file_scripts_missing_ref_project"))
    env_manager = EnvManager(poetry)
    venv_path = tmp_path / "venv"
    env_manager.build_venv(venv_path)
    tmp_venv = VirtualEnv(venv_path)

    io = BufferedIO()
    builder = EditableBuilder(poetry, tmp_venv, io)
    builder.build()

    # The file script for the missing reference must not be created
    script_path = tmp_venv._bin_dir.joinpath("missing-script")
    assert not script_path.exists()

    # The error message should be logged
    error_output = io.fetch_error()
    assert "missing-script" in error_output
    assert "does not exist" in error_output


def test_builder_skips_directory_file_script(
    fixture_dir: FixtureDirGetter,
    tmp_path: Path,
) -> None:
    from cleo.io.buffered_io import BufferedIO

    poetry = Factory().create_poetry(fixture_dir("file_scripts_dir_ref_project"))
    env_manager = EnvManager(poetry)
    venv_path = tmp_path / "venv"
    env_manager.build_venv(venv_path)
    tmp_venv = VirtualEnv(venv_path)

    io = BufferedIO()
    builder = EditableBuilder(poetry, tmp_venv, io)
    builder.build()

    # The file script for the directory reference must not be created
    script_path = tmp_venv._bin_dir.joinpath("dir-script")
    assert not script_path.exists()

    # The error message should be logged
    error_output = io.fetch_error()
    assert "dir-script" in error_output
    assert "is not a file" in error_output


def test_builder_skips_file_script_missing_reference_field(
    fixture_dir: FixtureDirGetter,
    tmp_path: Path,
) -> None:
    from cleo.io.buffered_io import BufferedIO

    poetry = Factory().create_poetry(
        fixture_dir("file_scripts_no_ref_field_project")
    )
    env_manager = EnvManager(poetry)
    venv_path = tmp_path / "venv"
    env_manager.build_venv(venv_path)
    tmp_venv = VirtualEnv(venv_path)

    io = BufferedIO()
    builder = EditableBuilder(poetry, tmp_venv, io)
    builder.build()

    # The file script with missing reference field must not be created
    script_path = tmp_venv._bin_dir.joinpath("no-ref-script")
    assert not script_path.exists()

    # The error message should be logged
    error_output = io.fetch_error()
    assert "no-ref-script" in error_output
    assert "reference" in error_output
