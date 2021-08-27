<<<<<<< HEAD
=======
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
import os
import shutil

from pathlib import Path
<<<<<<< HEAD
from typing import TYPE_CHECKING
=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

import pytest

from cleo.io.null_io import NullIO

from poetry.factory import Factory
from poetry.masonry.builders.editable import EditableBuilder
from poetry.utils.env import EnvManager
from poetry.utils.env import MockEnv
from poetry.utils.env import VirtualEnv


<<<<<<< HEAD
if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry


@pytest.fixture()
def simple_poetry() -> "Poetry":
=======
@pytest.fixture()
def simple_poetry():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    poetry = Factory().create_poetry(
        Path(__file__).parent.parent.parent / "fixtures" / "simple_project"
    )

    return poetry


@pytest.fixture()
<<<<<<< HEAD
def project_with_include() -> "Poetry":
=======
def project_with_include():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    poetry = Factory().create_poetry(
        Path(__file__).parent.parent.parent / "fixtures" / "with-include"
    )

    return poetry


@pytest.fixture()
<<<<<<< HEAD
def extended_poetry() -> "Poetry":
=======
def extended_poetry():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    poetry = Factory().create_poetry(
        Path(__file__).parent.parent.parent / "fixtures" / "extended_project"
    )

    return poetry


@pytest.fixture()
<<<<<<< HEAD
def extended_without_setup_poetry() -> "Poetry":
=======
def extended_without_setup_poetry():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    poetry = Factory().create_poetry(
        Path(__file__).parent.parent.parent
        / "fixtures"
        / "extended_project_without_setup"
    )

    return poetry


@pytest.fixture()
<<<<<<< HEAD
def env_manager(simple_poetry: "Poetry") -> EnvManager:
=======
def env_manager(simple_poetry):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return EnvManager(simple_poetry)


@pytest.fixture
<<<<<<< HEAD
def tmp_venv(tmp_dir: str, env_manager: EnvManager) -> VirtualEnv:
=======
def tmp_venv(tmp_dir, env_manager):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    venv_path = Path(tmp_dir) / "venv"

    env_manager.build_venv(str(venv_path))

    venv = VirtualEnv(venv_path)
    yield venv

    shutil.rmtree(str(venv.path))


<<<<<<< HEAD
def test_builder_installs_proper_files_for_standard_packages(
    simple_poetry: "Poetry", tmp_venv: VirtualEnv
):
=======
def test_builder_installs_proper_files_for_standard_packages(simple_poetry, tmp_venv):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

<<<<<<< HEAD
    assert dist_info.joinpath("INSTALLER").read_text() == "poetry"
    assert (
        dist_info.joinpath("entry_points.txt").read_text()
        == "[console_scripts]\nbaz=bar:baz.boom.bim\nfoo=foo:bar\nfox=fuz.foo:bar.baz\n\n"
=======
    assert "poetry" == dist_info.joinpath("INSTALLER").read_text()
    assert (
        "[console_scripts]\nbaz=bar:baz.boom.bim\nfoo=foo:bar\nfox=fuz.foo:bar.baz\n\n"
        == dist_info.joinpath("entry_points.txt").read_text()
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
Classifier: Topic :: Software Development :: Build Tools
Classifier: Topic :: Software Development :: Libraries :: Python Modules
Project-URL: Documentation, https://python-poetry.org/docs
Project-URL: Repository, https://github.com/python-poetry/poetry
Description-Content-Type: text/x-rst

My Package
==========

"""
    assert metadata == dist_info.joinpath("METADATA").read_text(encoding="utf-8")

    records = dist_info.joinpath("RECORD").read_text()
    pth_file = "simple_project.pth"
    assert tmp_venv.site_packages.exists(pth_file)
    assert str(tmp_venv.site_packages.find(pth_file)[0]) in records
    assert str(tmp_venv._bin_dir.joinpath("foo")) in records
    assert str(tmp_venv._bin_dir.joinpath("baz")) in records
    assert str(dist_info.joinpath("METADATA")) in records
    assert str(dist_info.joinpath("INSTALLER")) in records
    assert str(dist_info.joinpath("entry_points.txt")) in records
    assert str(dist_info.joinpath("RECORD")) in records

<<<<<<< HEAD
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
=======
    baz_script = """\
#!{python}
from bar import baz

if __name__ == '__main__':
    baz.boom.bim()
""".format(
        python=tmp_venv.python
    )

    assert baz_script == tmp_venv._bin_dir.joinpath("baz").read_text()

    foo_script = """\
#!{python}
from foo import bar

if __name__ == '__main__':
    bar()
""".format(
        python=tmp_venv.python
    )

    assert foo_script == tmp_venv._bin_dir.joinpath("foo").read_text()

    fox_script = """\
#!{python}
from fuz.foo import bar

if __name__ == '__main__':
    bar.baz()
""".format(
        python=tmp_venv.python
    )
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

    assert fox_script == tmp_venv._bin_dir.joinpath("fox").read_text()


def test_builder_falls_back_on_setup_and_pip_for_packages_with_build_scripts(
<<<<<<< HEAD
    mocker: "MockerFixture", extended_poetry: "Poetry", tmp_dir: str
=======
    mocker, extended_poetry, tmp_dir
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    pip_editable_install = mocker.patch(
        "poetry.masonry.builders.editable.pip_editable_install"
    )
    env = MockEnv(path=Path(tmp_dir) / "foo")
    builder = EditableBuilder(extended_poetry, env, NullIO())

    builder.build()
    pip_editable_install.assert_called_once_with(
        extended_poetry.pyproject.file.path.parent, env
    )
    assert [] == env.executed


def test_builder_installs_proper_files_when_packages_configured(
<<<<<<< HEAD
    project_with_include: "Poetry", tmp_venv: VirtualEnv
=======
    project_with_include, tmp_venv
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_builder_should_execute_build_scripts(
    extended_without_setup_poetry: "Poetry", tmp_dir: str
):
=======
def test_builder_should_execute_build_scripts(extended_without_setup_poetry, tmp_dir):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    env = MockEnv(path=Path(tmp_dir) / "foo")
    builder = EditableBuilder(extended_without_setup_poetry, env, NullIO())

    builder.build()

    assert [
        ["python", str(extended_without_setup_poetry.file.parent / "build.py")]
    ] == env.executed
