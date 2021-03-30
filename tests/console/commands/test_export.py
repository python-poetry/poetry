# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from tests.helpers import get_package


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
def setup(repo):
    repo.add_package(get_package("foo", "1.0.0"))
    repo.add_package(get_package("bar", "1.1.0"))


@pytest.fixture
def poetry(project_factory):
    return project_factory(name="export", pyproject_content=PYPROJECT_CONTENT)


@pytest.fixture
def tester(command_tester_factory, poetry):
    return command_tester_factory("export", poetry=poetry)


def _export_requirements(tester, poetry):
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


def test_export_exports_requirements_txt_file_locks_if_no_lock_file(tester, poetry):
    assert not poetry.locker.lock.exists()
    _export_requirements(tester, poetry)
    assert "The lock file does not exist. Locking." in tester.io.fetch_output()


def test_export_exports_requirements_txt_uses_lock_file(tester, poetry, do_lock):
    _export_requirements(tester, poetry)
    assert "The lock file does not exist. Locking." not in tester.io.fetch_output()


def test_export_fails_on_invalid_format(tester, do_lock):
    with pytest.raises(ValueError):
        tester.execute("--format invalid")


def test_export_prints_to_stdout_by_default(tester, do_lock):
    tester.execute("--format requirements.txt")
    expected = """\
foo==1.0.0
"""
    assert expected == tester.io.fetch_output()


def test_export_uses_requirements_txt_format_by_default(tester, do_lock):
    tester.execute()
    expected = """\
foo==1.0.0
"""
    assert expected == tester.io.fetch_output()


def test_export_includes_extras_by_flag(tester, do_lock):
    tester.execute("--format requirements.txt --extras feature_bar")
    expected = """\
bar==1.1.0
foo==1.0.0
"""
    assert expected == tester.io.fetch_output()
