from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from deepdiff import DeepDiff
from packaging.utils import canonicalize_name
from poetry.core.constraints.version import parse_constraint
from poetry.core.toml.file import TOMLFile

from poetry.factory import Factory
from poetry.plugins.plugin import Plugin
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.pypi_repository import PyPiRepository
from tests.helpers import mock_metadata_entry_points


if TYPE_CHECKING:
    from cleo.io.io import IO
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.types import FixtureDirGetter

fixtures_dir = Path(__file__).parent / "fixtures"


class MyPlugin(Plugin):
    def activate(self, poetry: Poetry, io: IO) -> None:
        io.write_line("Setting readmes")
        poetry.package.readmes = ("README.md",)


def test_create_poetry():
    poetry = Factory().create_poetry(fixtures_dir / "sample_project")

    package = poetry.package

    assert package.name == "my-package"
    assert package.version.text == "1.2.3"
    assert package.description == "Some description."
    assert package.authors == ["Sébastien Eustace <sebastien@eustace.io>"]
    assert package.license.id == "MIT"

    for readme in package.readmes:
        assert (
            readme.relative_to(fixtures_dir).as_posix() == "sample_project/README.rst"
        )

    assert package.homepage == "https://python-poetry.org"
    assert package.repository_url == "https://github.com/python-poetry/poetry"
    assert package.keywords == ["packaging", "dependency", "poetry"]

    assert package.python_versions == "~2.7 || ^3.6"
    assert str(package.python_constraint) == ">=2.7,<2.8 || >=3.6,<4.0"

    dependencies = {}
    for dep in package.requires:
        dependencies[dep.name] = dep

    cleo = dependencies["cleo"]
    assert cleo.pretty_constraint == "^0.6"
    assert not cleo.is_optional()

    pendulum = dependencies["pendulum"]
    assert pendulum.pretty_constraint == "branch 2.0"
    assert pendulum.is_vcs()
    assert pendulum.vcs == "git"
    assert pendulum.branch == "2.0"
    assert pendulum.source == "https://github.com/sdispater/pendulum.git"
    assert pendulum.allows_prereleases()

    requests = dependencies["requests"]
    assert requests.pretty_constraint == "^2.18"
    assert not requests.is_vcs()
    assert not requests.allows_prereleases()
    assert requests.is_optional()
    assert requests.extras == frozenset(["security"])

    pathlib2 = dependencies["pathlib2"]
    assert pathlib2.pretty_constraint == "^2.2"
    assert parse_constraint(pathlib2.python_versions) == parse_constraint("~2.7")
    assert not pathlib2.is_optional()

    demo = dependencies["demo"]
    assert demo.is_file()
    assert not demo.is_vcs()
    assert demo.name == "demo"
    assert demo.pretty_constraint == "*"

    demo = dependencies["my-package"]
    assert not demo.is_file()
    assert demo.is_directory()
    assert not demo.is_vcs()
    assert demo.name == "my-package"
    assert demo.pretty_constraint == "*"

    simple_project = dependencies["simple-project"]
    assert not simple_project.is_file()
    assert simple_project.is_directory()
    assert not simple_project.is_vcs()
    assert simple_project.name == "simple-project"
    assert simple_project.pretty_constraint == "*"

    functools32 = dependencies["functools32"]
    assert functools32.name == "functools32"
    assert functools32.pretty_constraint == "^3.2.3"
    assert (
        str(functools32.marker)
        == 'python_version ~= "2.7" and sys_platform == "win32" or python_version in'
        ' "3.4 3.5"'
    )

    assert "db" in package.extras

    classifiers = package.classifiers

    assert classifiers == [
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]

    assert package.all_classifiers == [
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]


@pytest.mark.parametrize(
    ("project",),
    [
        ("simple_project",),
        ("project_with_extras",),
    ],
)
def test_create_pyproject_from_package(project: str):
    poetry = Factory().create_poetry(fixtures_dir / project)
    package = poetry.package

    pyproject = Factory.create_pyproject_from_package(package)

    result = pyproject["tool"]["poetry"]
    expected = poetry.pyproject.poetry_config

    # Extras are normalized as they are read.
    extras = expected.pop("extras", None)
    if extras is not None:
        normalized_extras = {
            canonicalize_name(extra): dependencies
            for extra, dependencies in extras.items()
        }
        expected["extras"] = normalized_extras

    # packages do not support this at present
    expected.pop("scripts", None)

    # remove any empty sections
    sections = list(expected.keys())
    for section in sections:
        if not expected[section]:
            expected.pop(section)

    assert not DeepDiff(expected, result)


def test_create_poetry_with_packages_and_includes():
    poetry = Factory().create_poetry(fixtures_dir / "with-include")

    package = poetry.package

    assert package.packages == [
        {"include": "extra_dir/**/*.py"},
        {"include": "extra_dir/**/*.py"},
        {"include": "my_module.py"},
        {"include": "package_with_include"},
        {"include": "tests", "format": "sdist"},
        {"include": "for_wheel_only", "format": ["wheel"]},
        {"include": "src_package", "from": "src"},
    ]

    assert package.include == [
        {"path": "extra_dir/vcs_excluded.txt", "format": []},
        {"path": "notes.txt", "format": []},
    ]


def test_create_poetry_with_multi_constraints_dependency():
    poetry = Factory().create_poetry(
        fixtures_dir / "project_with_multi_constraints_dependency"
    )

    package = poetry.package

    assert len(package.requires) == 2


def test_poetry_with_default_source(with_simple_keyring: None):
    poetry = Factory().create_poetry(fixtures_dir / "with_default_source")

    assert len(poetry.pool.repositories) == 1


def test_poetry_with_non_default_source(with_simple_keyring: None):
    poetry = Factory().create_poetry(fixtures_dir / "with_non_default_source")

    assert len(poetry.pool.repositories) == 2

    assert not poetry.pool.has_default()

    assert poetry.pool.repositories[0].name == "foo"
    assert isinstance(poetry.pool.repositories[0], LegacyRepository)

    assert poetry.pool.repositories[1].name == "PyPI"
    assert isinstance(poetry.pool.repositories[1], PyPiRepository)


def test_poetry_with_non_default_secondary_source(with_simple_keyring: None):
    poetry = Factory().create_poetry(fixtures_dir / "with_non_default_secondary_source")

    assert len(poetry.pool.repositories) == 2

    assert poetry.pool.has_default()

    repository = poetry.pool.repositories[0]
    assert repository.name == "PyPI"
    assert isinstance(repository, PyPiRepository)

    repository = poetry.pool.repositories[1]
    assert repository.name == "foo"
    assert isinstance(repository, LegacyRepository)


def test_poetry_with_non_default_multiple_secondary_sources(with_simple_keyring: None):
    poetry = Factory().create_poetry(
        fixtures_dir / "with_non_default_multiple_secondary_sources"
    )

    assert len(poetry.pool.repositories) == 3

    assert poetry.pool.has_default()

    repository = poetry.pool.repositories[0]
    assert repository.name == "PyPI"
    assert isinstance(repository, PyPiRepository)

    repository = poetry.pool.repositories[1]
    assert repository.name == "foo"
    assert isinstance(repository, LegacyRepository)

    repository = poetry.pool.repositories[2]
    assert repository.name == "bar"
    assert isinstance(repository, LegacyRepository)


def test_poetry_with_non_default_multiple_sources(with_simple_keyring: None):
    poetry = Factory().create_poetry(fixtures_dir / "with_non_default_multiple_sources")

    assert len(poetry.pool.repositories) == 3

    assert not poetry.pool.has_default()

    repository = poetry.pool.repositories[0]
    assert repository.name == "bar"
    assert isinstance(repository, LegacyRepository)

    repository = poetry.pool.repositories[1]
    assert repository.name == "foo"
    assert isinstance(repository, LegacyRepository)

    repository = poetry.pool.repositories[2]
    assert repository.name == "PyPI"
    assert isinstance(repository, PyPiRepository)


def test_poetry_with_no_default_source():
    poetry = Factory().create_poetry(fixtures_dir / "sample_project")

    assert len(poetry.pool.repositories) == 1

    assert poetry.pool.has_default()

    assert poetry.pool.repositories[0].name == "PyPI"
    assert isinstance(poetry.pool.repositories[0], PyPiRepository)


def test_poetry_with_two_default_sources(with_simple_keyring: None):
    with pytest.raises(ValueError) as e:
        Factory().create_poetry(fixtures_dir / "with_two_default_sources")

    assert str(e.value) == "Only one repository can be the default."


def test_validate():
    complete = TOMLFile(fixtures_dir / "complete.toml")
    content = complete.read()["tool"]["poetry"]

    assert Factory.validate(content) == {"errors": [], "warnings": []}


def test_validate_fails():
    complete = TOMLFile(fixtures_dir / "complete.toml")
    content = complete.read()["tool"]["poetry"]
    content["this key is not in the schema"] = ""

    expected = (
        "Additional properties are not allowed "
        "('this key is not in the schema' was unexpected)"
    )

    assert Factory.validate(content) == {"errors": [expected], "warnings": []}


def test_create_poetry_fails_on_invalid_configuration():
    with pytest.raises(RuntimeError) as e:
        Factory().create_poetry(
            Path(__file__).parent / "fixtures" / "invalid_pyproject" / "pyproject.toml"
        )

    expected = """\
The Poetry configuration is invalid:
  - 'description' is a required property
"""
    assert str(e.value) == expected


def test_create_poetry_with_local_config(fixture_dir: FixtureDirGetter):
    poetry = Factory().create_poetry(fixture_dir("with_local_config"))

    assert not poetry.config.get("virtualenvs.in-project")
    assert not poetry.config.get("virtualenvs.create")
    assert not poetry.config.get("virtualenvs.options.always-copy")
    assert not poetry.config.get("virtualenvs.options.no-pip")
    assert not poetry.config.get("virtualenvs.options.no-setuptools")
    assert not poetry.config.get("virtualenvs.options.system-site-packages")


def test_create_poetry_with_plugins(mocker: MockerFixture):
    mock_metadata_entry_points(mocker, MyPlugin)

    poetry = Factory().create_poetry(fixtures_dir / "sample_project")

    assert poetry.package.readmes == ("README.md",)
