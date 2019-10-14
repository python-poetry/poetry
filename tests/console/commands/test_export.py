# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from cleo.testers import CommandTester

from poetry.factory import Factory
from poetry.repositories.pool import Pool
from tests.helpers import get_package

from ..conftest import Application
from ..conftest import Locker
from ..conftest import Path


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

homepage = "https://poetry.eustace.io"
repository = "https://github.com/sdispater/poetry"
documentation = "https://poetry.eustace.io/docs"

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


@pytest.fixture
def poetry(repo, tmp_dir):
    with (Path(tmp_dir) / "pyproject.toml").open("w", encoding="utf-8") as f:
        f.write(PYPROJECT_CONTENT)

    p = Factory().create_poetry(Path(tmp_dir))

    locker = Locker(p.locker.lock.path, p.locker._local_config)
    locker.write()
    p.set_locker(locker)

    pool = Pool()
    pool.add_repository(repo)
    p.set_pool(pool)

    yield p


@pytest.fixture
def app(poetry):
    return Application(poetry)


def test_export_exports_requirements_txt_file_locks_if_no_lock_file(app, repo):
    command = app.find("export")
    tester = CommandTester(command)

    assert not app.poetry.locker.lock.exists()

    repo.add_package(get_package("foo", "1.0.0"))
    repo.add_package(get_package("bar", "1.1.0"))

    tester.execute("--format requirements.txt --output requirements.txt")

    requirements = app.poetry.file.parent / "requirements.txt"
    assert requirements.exists()

    with requirements.open(encoding="utf-8") as f:
        content = f.read()

    assert app.poetry.locker.lock.exists()

    expected = """\
foo==1.0.0
"""

    assert expected == content
    assert "The lock file does not exist. Locking." in tester.io.fetch_output()


def test_export_exports_requirements_txt_uses_lock_file(app, repo):
    repo.add_package(get_package("foo", "1.0.0"))
    repo.add_package(get_package("bar", "1.1.0"))

    command = app.find("lock")
    tester = CommandTester(command)
    tester.execute()

    assert app.poetry.locker.lock.exists()

    command = app.find("export")
    tester = CommandTester(command)

    tester.execute("--format requirements.txt --output requirements.txt")

    requirements = app.poetry.file.parent / "requirements.txt"
    assert requirements.exists()

    with requirements.open(encoding="utf-8") as f:
        content = f.read()

    assert app.poetry.locker.lock.exists()

    expected = """\
foo==1.0.0
"""

    assert expected == content
    assert "The lock file does not exist. Locking." not in tester.io.fetch_output()


def test_export_fails_on_invalid_format(app, repo):
    repo.add_package(get_package("foo", "1.0.0"))
    repo.add_package(get_package("bar", "1.1.0"))

    command = app.find("lock")
    tester = CommandTester(command)
    tester.execute()

    assert app.poetry.locker.lock.exists()

    command = app.find("export")
    tester = CommandTester(command)

    with pytest.raises(ValueError):
        tester.execute("--format invalid")


def test_export_prints_to_stdout_by_default(app, repo):
    repo.add_package(get_package("foo", "1.0.0"))
    repo.add_package(get_package("bar", "1.1.0"))

    command = app.find("lock")
    tester = CommandTester(command)
    tester.execute()

    assert app.poetry.locker.lock.exists()

    command = app.find("export")
    tester = CommandTester(command)

    tester.execute("--format requirements.txt")

    expected = """\
foo==1.0.0
"""

    assert expected == tester.io.fetch_output()


def test_export_includes_extras_by_flag(app, repo):
    repo.add_package(get_package("foo", "1.0.0"))
    repo.add_package(get_package("bar", "1.1.0"))

    command = app.find("lock")
    tester = CommandTester(command)
    tester.execute()

    assert app.poetry.locker.lock.exists()

    command = app.find("export")
    tester = CommandTester(command)

    tester.execute("--format requirements.txt --extras feature_bar")

    expected = """\
bar==1.1.0
foo==1.0.0
"""

    assert expected == tester.io.fetch_output()
