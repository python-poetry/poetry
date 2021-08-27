<<<<<<< HEAD
from typing import TYPE_CHECKING
from unittest.mock import ANY
from unittest.mock import Mock

import pytest

from poetry.console.commands.export import Exporter
from tests.helpers import get_package


if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch
    from cleo.testers.command_tester import CommandTester

    from poetry.poetry import Poetry
    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory
    from tests.types import ProjectFactory


=======
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from tests.helpers import get_package


>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
PYPROJECT_CONTENT = """\
[tool.poetry]
name = "simple-project"
version = "1.2.3"
description = "Some description."
authors = [
    "Sébastien Eustace <sebastien@eustace.io>"
]
license = "MIT"

readme = "README.rst"

homepage = "https://python-poetry.org"
repository = "https://github.com/python-poetry/poetry"
documentation = "https://python-poetry.org/docs"

keywords = ["packaging", "dependency", "poetry"]

classifiers = [
    "Topic :: Software Development :: Build Tools",
    "Topic :: Software Development :: Libraries :: Python Modules"
]

# Requirements
[tool.poetry.dependencies]
python = "~2.7 || ^3.4"
foo = "^1.0"
bar = { version = "^1.1", optional = true }

[tool.poetry.extras]
feature_bar = ["bar"]
"""


@pytest.fixture(autouse=True)
<<<<<<< HEAD
def setup(repo: "TestRepository") -> None:
=======
def setup(repo):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    repo.add_package(get_package("foo", "1.0.0"))
    repo.add_package(get_package("bar", "1.1.0"))


@pytest.fixture
<<<<<<< HEAD
def poetry(project_factory: "ProjectFactory") -> "Poetry":
=======
def poetry(project_factory):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return project_factory(name="export", pyproject_content=PYPROJECT_CONTENT)


@pytest.fixture
<<<<<<< HEAD
def tester(
    command_tester_factory: "CommandTesterFactory", poetry: "Poetry"
) -> "CommandTester":
    return command_tester_factory("export", poetry=poetry)


def _export_requirements(tester: "CommandTester", poetry: "Poetry") -> None:
=======
def tester(command_tester_factory, poetry):
    return command_tester_factory("export", poetry=poetry)


def _export_requirements(tester, poetry):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute("--format requirements.txt --output requirements.txt")

    requirements = poetry.file.parent / "requirements.txt"
    assert requirements.exists()

    with requirements.open(encoding="utf-8") as f:
        content = f.read()

    assert poetry.locker.lock.exists()

    expected = """\
foo==1.0.0
"""

    assert expected == content


<<<<<<< HEAD
def test_export_exports_requirements_txt_file_locks_if_no_lock_file(
    tester: "CommandTester", poetry: "Poetry"
):
    assert not poetry.locker.lock.exists()
    _export_requirements(tester, poetry)
    assert "The lock file does not exist. Locking." in tester.io.fetch_error()


def test_export_exports_requirements_txt_uses_lock_file(
    tester: "CommandTester", poetry: "Poetry", do_lock: None
):
    _export_requirements(tester, poetry)
    assert "The lock file does not exist. Locking." not in tester.io.fetch_error()


def test_export_fails_on_invalid_format(tester: "CommandTester", do_lock: None):
=======
def test_export_exports_requirements_txt_file_locks_if_no_lock_file(tester, poetry):
    assert not poetry.locker.lock.exists()
    _export_requirements(tester, poetry)
    assert "The lock file does not exist. Locking." in tester.io.fetch_output()


def test_export_exports_requirements_txt_uses_lock_file(tester, poetry, do_lock):
    _export_requirements(tester, poetry)
    assert "The lock file does not exist. Locking." not in tester.io.fetch_output()


def test_export_fails_on_invalid_format(tester, do_lock):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    with pytest.raises(ValueError):
        tester.execute("--format invalid")


<<<<<<< HEAD
def test_export_prints_to_stdout_by_default(tester: "CommandTester", do_lock: None):
=======
def test_export_prints_to_stdout_by_default(tester, do_lock):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute("--format requirements.txt")
    expected = """\
foo==1.0.0
"""
    assert expected == tester.io.fetch_output()


<<<<<<< HEAD
def test_export_uses_requirements_txt_format_by_default(
    tester: "CommandTester", do_lock: None
):
=======
def test_export_uses_requirements_txt_format_by_default(tester, do_lock):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute()
    expected = """\
foo==1.0.0
"""
    assert expected == tester.io.fetch_output()


<<<<<<< HEAD
def test_export_includes_extras_by_flag(tester: "CommandTester", do_lock: None):
=======
def test_export_includes_extras_by_flag(tester, do_lock):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute("--format requirements.txt --extras feature_bar")
    expected = """\
bar==1.1.0
foo==1.0.0
"""
    assert expected == tester.io.fetch_output()
<<<<<<< HEAD


def test_export_with_urls(
    monkeypatch: "MonkeyPatch", tester: "CommandTester", poetry: "Poetry"
):
    """
    We are just validating that the option gets passed. The option itself is tested in
    the Exporter test.
    """
    mock_export = Mock()
    monkeypatch.setattr(Exporter, "export", mock_export)
    tester.execute("--without-urls")
    mock_export.assert_called_once_with(
        ANY,
        ANY,
        ANY,
        dev=False,
        extras=[],
        with_credentials=False,
        with_hashes=True,
        with_urls=False,
    )
=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
