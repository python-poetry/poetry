# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from cleo.testers import CommandTester

from poetry.repositories.auth import Auth
from poetry.repositories.legacy_repository import LegacyRepository
from tests.helpers import get_package

from ..conftest import Application, Config
from ..conftest import Path
from ..conftest import Poetry


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
"""


@pytest.fixture
def legacy_repo():
    auth = Auth("https://pypi.myserver.com:443/simple", "johndoe#$%", "passwd123(*(")
    return LegacyRepository("private", auth._url, auth)


@pytest.fixture
def poetry(repo, legacy_repo, tmp_dir):
    with (Path(tmp_dir) / "pyproject.toml").open("w", encoding="utf-8") as f:
        f.write(PYPROJECT_CONTENT)

    p = Poetry.create(Path(tmp_dir))
    p._auth_config = Config(None)
    p.auth_config.add_property(
        "http-basic.private.username", legacy_repo._auth._username
    )
    p.auth_config.add_property(
        "http-basic.private.password", legacy_repo._auth._password
    )

    p.pool.remove_repository("pypi")
    p.pool.add_repository(repo)
    p.pool.add_repository(legacy_repo)
    p._locker.write()

    yield p


@pytest.fixture
def app(poetry):
    return Application(poetry)


def test_export_exports_requirements_txt_file_locks_if_no_lock_file(app, repo):
    command = app.find("export")
    tester = CommandTester(command)

    assert not app.poetry.locker.lock.exists()

    repo.add_package(get_package("foo", "1.0.0"))

    tester.execute("--format requirements.txt")

    requirements = app.poetry.file.parent / "requirements.txt"
    assert requirements.exists()

    with requirements.open(encoding="utf-8") as f:
        content = f.read()

    assert app.poetry.locker.lock.exists()

    expected = """\
--extra-index-url https://johndoe%23%24%25:passwd123%28%2A%28@pypi.myserver.com:443/simple
foo==1.0.0
"""

    assert expected == content
    assert "The lock file does not exist. Locking." in tester.io.fetch_output()


def test_export_exports_requirements_txt_uses_lock_file(app, repo):
    repo.add_package(get_package("foo", "1.0.0"))

    command = app.find("lock")
    tester = CommandTester(command)
    tester.execute()

    assert app.poetry.locker.lock.exists()

    command = app.find("export")
    tester = CommandTester(command)

    tester.execute("--format requirements.txt")

    requirements = app.poetry.file.parent / "requirements.txt"
    assert requirements.exists()

    with requirements.open(encoding="utf-8") as f:
        content = f.read()

    assert app.poetry.locker.lock.exists()

    expected = """\
--extra-index-url https://johndoe%23%24%25:passwd123%28%2A%28@pypi.myserver.com:443/simple
foo==1.0.0
"""

    assert expected == content
    assert "The lock file does not exist. Locking." not in tester.io.fetch_output()


def test_export_fails_on_invalid_format(app, repo):
    repo.add_package(get_package("foo", "1.0.0"))

    command = app.find("lock")
    tester = CommandTester(command)
    tester.execute()

    assert app.poetry.locker.lock.exists()

    command = app.find("export")
    tester = CommandTester(command)

    with pytest.raises(ValueError):
        tester.execute("--format invalid")
