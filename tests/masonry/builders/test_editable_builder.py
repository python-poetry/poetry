from __future__ import annotations

import csv
import json
import os
import shutil

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cleo.io.null_io import NullIO
from deepdiff import DeepDiff
from poetry.core.constraints.version import Version

from poetry.factory import Factory
from poetry.masonry.builders.editable import EditableBuilder
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils.env import EnvCommandError
from poetry.utils.env import EnvManager
from poetry.utils.env import MockEnv
from poetry.utils.env import VirtualEnv
from poetry.utils.env import ephemeral_environment


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry


@pytest.fixture()
def simple_poetry() -> Poetry:
    poetry = Factory().create_poetry(
        Path(__file__).parent.parent.parent / "fixtures" / "simple_project"
    )

    return poetry


@pytest.fixture()
def project_with_include() -> Poetry:
    poetry = Factory().create_poetry(
        Path(__file__).parent.parent.parent / "fixtures" / "with-include"
    )

    return poetry


@pytest.fixture()
def extended_poetry() -> Poetry:
    poetry = Factory().create_poetry(
        Path(__file__).parent.parent.parent / "fixtures" / "extended_project"
    )

    return poetry


@pytest.fixture()
def extended_without_setup_poetry() -> Poetry:
    poetry = Factory().create_poetry(
        Path(__file__).parent.parent.parent
        / "fixtures"
        / "extended_project_without_setup"
    )

    return poetry


@pytest.fixture()
def env_manager(simple_poetry: Poetry) -> EnvManager:
    return EnvManager(simple_poetry)


@pytest.fixture
def tmp_venv(tmp_dir: str, env_manager: EnvManager) -> VirtualEnv:
    venv_path = Path(tmp_dir) / "venv"

    env_manager.build_venv(str(venv_path))

    venv = VirtualEnv(venv_path)
    yield venv

    shutil.rmtree(str(venv.path))


def test_builder_installs_proper_files_for_standard_packages(
    simple_poetry: Poetry, tmp_venv: VirtualEnv
):
    builder = EditableBuilder(simple_poetry, tmp_venv, NullIO())

    builder.build()

    assert tmp_venv._bin_dir.joinpath("foo").exists()
    pth_file = "simple_project.pth"
    assert tmp_venv.site_packages.exists(pth_file)
    assert (
        simple_poetry.file.parent.resolve().as_posix()
        == tmp_venv.site_packages.find(pth_file)[0].read_text().strip(os.linesep)
    )

    dist_info = "simple_project-1.2.3.dist-info"
    assert tmp_venv.site_packages.exists(dist_info)

    dist_info = tmp_venv.site_packages.find(dist_info)[0]

    assert dist_info.joinpath("INSTALLER").exists()
    assert dist_info.joinpath("METADATA").exists()
    assert dist_info.joinpath("RECORD").exists()
    assert dist_info.joinpath("entry_points.txt").exists()
    assert dist_info.joinpath("direct_url.json").exists()

    assert not DeepDiff(
        {
            "dir_info": {"editable": True},
            "url": simple_poetry.file.path.parent.as_uri(),
        },
        json.loads(dist_info.joinpath("direct_url.json").read_text()),
    )

    assert dist_info.joinpath("INSTALLER").read_text() == "poetry"
    assert (
        dist_info.joinpath("entry_points.txt").read_text()
        == "[console_scripts]\nbaz=bar:baz.boom.bim\nfoo=foo:bar\n"
        "fox=fuz.foo:bar.baz\n\n"
    )

    metadata = """\
Metadata-Version: 2.1
Name: simple-project
Version: 1.2.3
Summary: Some description.
Home-page: https://python-poetry.org
License: MIT
Keywords: packaging,dependency,poetry
Author: Sébastien Eustace
Author-email: sebastien@eustace.io
Requires-Python: >=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*
Classifier: License :: OSI Approved :: MIT License
Classifier: Programming Language :: Python :: 2
Classifier: Programming Language :: Python :: 2.7
Classifier: Programming Language :: Python :: 3
Classifier: Programming Language :: Python :: 3.4
Classifier: Programming Language :: Python :: 3.5
Classifier: Programming Language :: Python :: 3.6
Classifier: Programming Language :: Python :: 3.7
Classifier: Programming Language :: Python :: 3.8
Classifier: Programming Language :: Python :: 3.9
Classifier: Programming Language :: Python :: 3.10
Classifier: Programming Language :: Python :: 3.11
Classifier: Topic :: Software Development :: Build Tools
Classifier: Topic :: Software Development :: Libraries :: Python Modules
Project-URL: Documentation, https://python-poetry.org/docs
Project-URL: Repository, https://github.com/python-poetry/poetry
Description-Content-Type: text/x-rst

My Package
==========

"""
    assert metadata == dist_info.joinpath("METADATA").read_text(encoding="utf-8")

    with open(dist_info.joinpath("RECORD"), encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        records = list(reader)

    assert all(len(row) == 3 for row in records)
    record_entries = {row[0] for row in records}
    pth_file = "simple_project.pth"
    assert tmp_venv.site_packages.exists(pth_file)
    assert str(tmp_venv.site_packages.find(pth_file)[0]) in record_entries
    assert str(tmp_venv._bin_dir.joinpath("foo")) in record_entries
    assert str(tmp_venv._bin_dir.joinpath("baz")) in record_entries
    assert str(dist_info.joinpath("METADATA")) in record_entries
    assert str(dist_info.joinpath("INSTALLER")) in record_entries
    assert str(dist_info.joinpath("entry_points.txt")) in record_entries
    assert str(dist_info.joinpath("RECORD")) in record_entries
    assert str(dist_info.joinpath("direct_url.json")) in record_entries

    baz_script = f"""\
#!{tmp_venv.python}
import sys
from bar import baz

if __name__ == '__main__':
    sys.exit(baz.boom.bim())
"""

    assert baz_script == tmp_venv._bin_dir.joinpath("baz").read_text()

    foo_script = f"""\
#!{tmp_venv.python}
import sys
from foo import bar

if __name__ == '__main__':
    sys.exit(bar())
"""

    assert foo_script == tmp_venv._bin_dir.joinpath("foo").read_text()

    fox_script = f"""\
#!{tmp_venv.python}
import sys
from fuz.foo import bar

if __name__ == '__main__':
    sys.exit(bar.baz())
"""

    assert fox_script == tmp_venv._bin_dir.joinpath("fox").read_text()


def test_builder_falls_back_on_setup_and_pip_for_packages_with_build_scripts(
    mocker: MockerFixture, extended_poetry: Poetry, tmp_dir: str
):
    pip_install = mocker.patch("poetry.masonry.builders.editable.pip_install")
    env = MockEnv(path=Path(tmp_dir) / "foo")
    builder = EditableBuilder(extended_poetry, env, NullIO())

    builder.build()
    pip_install.assert_called_once_with(
        extended_poetry.pyproject.file.path.parent, env, upgrade=True, editable=True
    )
    assert [] == env.executed


def test_builder_setup_generation_runs_with_pip_editable(tmp_dir: str) -> None:
    # create an isolated copy of the project
    fixture = Path(__file__).parent.parent.parent / "fixtures" / "extended_project"
    extended_project = Path(tmp_dir) / "extended_project"

    shutil.copytree(fixture, extended_project)
    assert extended_project.exists()

    poetry = Factory().create_poetry(extended_project)

    # we need a venv with setuptools since we are verifying setup.py builds
    with ephemeral_environment(flags={"no-setuptools": False}) as venv:
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
):
    builder = EditableBuilder(project_with_include, tmp_venv, NullIO())
    builder.build()

    pth_file = "with_include.pth"
    assert tmp_venv.site_packages.exists(pth_file)

    pth_file = tmp_venv.site_packages.find(pth_file)[0]

    paths = set()
    with pth_file.open() as f:
        for line in f.readlines():
            line = line.strip(os.linesep)
            if line:
                paths.add(line)

    project_root = project_with_include.file.parent.resolve()
    expected = {project_root.as_posix(), project_root.joinpath("src").as_posix()}

    assert paths.issubset(expected)
    assert len(paths) == len(expected)


def test_builder_should_execute_build_scripts(
    mocker: MockerFixture, extended_without_setup_poetry: Poetry, tmp_path: Path
):
    env = MockEnv(path=tmp_path / "foo")
    mocker.patch(
        "poetry.masonry.builders.editable.build_environment"
    ).return_value.__enter__.return_value = env

    builder = EditableBuilder(extended_without_setup_poetry, env, NullIO())

    builder.build()

    assert [
        ["python", str(extended_without_setup_poetry.file.parent / "build.py")]
    ] == env.executed
