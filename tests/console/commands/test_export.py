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
def setup(repo: "TestRepository") -> None:
    repo.add_package(get_package("foo", "1.0.0"))
    repo.add_package(get_package("bar", "1.1.0"))


@pytest.fixture
def poetry(project_factory: "ProjectFactory") -> "Poetry":
    return project_factory(name="export", pyproject_content=PYPROJECT_CONTENT)


@pytest.fixture
def tester(
    command_tester_factory: "CommandTesterFactory", poetry: "Poetry"
) -> "CommandTester":
    return command_tester_factory("export", poetry=poetry)


def _export_requirements(tester: "CommandTester", poetry: "Poetry") -> None:
    tester.execute("--format requirements.txt --output requirements.txt")

    requirements = poetry.file.parent / "requirements.txt"
    assert requirements.exists()

    with requirements.open(encoding="utf-8") as f:
        content = f.read()

    assert poetry.locker.lock.exists()

    expected = """\
foo==1.0.0
"""

    assert content == expected


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
    with pytest.raises(ValueError):
        tester.execute("--format invalid")


def test_export_prints_to_stdout_by_default(tester: "CommandTester", do_lock: None):
    tester.execute("--format requirements.txt")
    expected = """\
foo==1.0.0
"""
    assert tester.io.fetch_output() == expected


def test_export_uses_requirements_txt_format_by_default(
    tester: "CommandTester", do_lock: None
):
    tester.execute()
    expected = """\
foo==1.0.0
"""
    assert tester.io.fetch_output() == expected


def test_export_includes_extras_by_flag(tester: "CommandTester", do_lock: None):
    tester.execute("--format requirements.txt --extras feature_bar")
    expected = """\
bar==1.1.0
foo==1.0.0
"""
    assert tester.io.fetch_output() == expected


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
