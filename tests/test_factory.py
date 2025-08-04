from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

from cleo.io.buffered_io import BufferedIO
from deepdiff.diff import DeepDiff
from packaging.utils import canonicalize_name
from poetry.core.constraints.version import Version
from poetry.core.constraints.version import parse_constraint
from poetry.core.packages.package import Package
from poetry.core.packages.vcs_dependency import VCSDependency

from poetry.__version__ import __version__
from poetry.exceptions import PoetryError
from poetry.factory import Factory
from poetry.plugins.plugin import Plugin
from poetry.repositories.exceptions import InvalidSourceError
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.pypi_repository import PyPiRepository
from poetry.repositories.repository_pool import Priority
from poetry.toml.file import TOMLFile
from tests.helpers import mock_metadata_entry_points


if TYPE_CHECKING:
    from cleo.io.io import IO
    from pytest_mock import MockerFixture

    from poetry.config.config import Config
    from poetry.poetry import Poetry
    from tests.types import FixtureDirGetter


class MyPlugin(Plugin):
    def activate(self, poetry: Poetry, io: IO) -> None:
        io.write_line("Setting readmes")
        poetry.package.readmes = (Path("README.md"),)


def test_create_poetry(fixture_dir: FixtureDirGetter) -> None:
    poetry = Factory().create_poetry(fixture_dir("sample_project"))

    package = poetry.package

    assert package.name == "sample-project"
    assert package.version.text == "1.2.3"
    assert package.description == "Some description."
    assert package.authors == ["Sébastien Eustace <sebastien@eustace.io>"]
    assert package.license is not None
    assert package.license.id == "MIT"

    for readme in package.readmes:
        assert (
            readme.relative_to(fixture_dir("sample_project")).as_posix() == "README.rst"
        )

    assert package.homepage == "https://python-poetry.org"
    assert package.repository_url == "https://github.com/python-poetry/poetry"
    assert package.keywords == ["packaging", "dependency", "poetry"]

    assert package.python_versions == "~2.7 || ^3.6"
    assert str(package.python_constraint) == ">=2.7,<2.8 || >=3.6,<4.0"

    dependencies = {}
    for dep in package.requires:
        dependencies[dep.name] = dep

    cleo = dependencies[canonicalize_name("cleo")]
    assert cleo.pretty_constraint == "^0.6"
    assert not cleo.is_optional()

    pendulum = dependencies[canonicalize_name("pendulum")]
    assert pendulum.pretty_constraint == "branch 2.0"
    assert pendulum.is_vcs()
    assert isinstance(pendulum, VCSDependency)
    assert pendulum.vcs == "git"
    assert pendulum.branch == "2.0"
    assert pendulum.source == "https://github.com/sdispater/pendulum.git"
    assert pendulum.allows_prereleases()

    requests = dependencies[canonicalize_name("requests")]
    assert requests.pretty_constraint == "^2.18"
    assert not requests.is_vcs()
    assert not requests.allows_prereleases()
    assert requests.is_optional()
    assert requests.extras == frozenset(["security"])

    pathlib2 = dependencies[canonicalize_name("pathlib2")]
    assert pathlib2.pretty_constraint == "^2.2"
    assert parse_constraint(pathlib2.python_versions) == parse_constraint("~2.7")
    assert not pathlib2.is_optional()

    demo = dependencies[canonicalize_name("demo")]
    assert demo.is_file()
    assert not demo.is_vcs()
    assert demo.name == "demo"
    assert demo.pretty_constraint == "*"

    demo = dependencies[canonicalize_name("my-package")]
    assert not demo.is_file()
    assert demo.is_directory()
    assert not demo.is_vcs()
    assert demo.name == "my-package"
    assert demo.pretty_constraint == "*"

    simple_project = dependencies[canonicalize_name("simple-project")]
    assert not simple_project.is_file()
    assert simple_project.is_directory()
    assert not simple_project.is_vcs()
    assert simple_project.name == "simple-project"
    assert simple_project.pretty_constraint == "*"

    functools32 = dependencies[canonicalize_name("functools32")]
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
        *(
            f"Programming Language :: Python :: {version}"
            for version in sorted(
                Package.AVAILABLE_PYTHONS,
                key=lambda x: tuple(map(int, x.split("."))),
            )
            if package.python_constraint.allows_any(
                parse_constraint(version + ".*")
                if len(version) == 1
                else Version.parse(version)
            )
        ),
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]


@pytest.mark.parametrize(
    ("project",),
    [
        ("simple_project_legacy",),
        ("project_with_extras",),
    ],
)
def test_create_pyproject_from_package(
    project: str, fixture_dir: FixtureDirGetter
) -> None:
    poetry = Factory().create_poetry(fixture_dir(project))
    package = poetry.package

    pyproject: dict[str, Any] = Factory.create_pyproject_from_package(package)

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


def test_create_poetry_with_packages_and_includes(
    fixture_dir: FixtureDirGetter,
) -> None:
    poetry = Factory().create_poetry(fixture_dir("with-include"))

    package = poetry.package

    assert package.packages == [
        {"include": "extra_dir/**/*.py", "format": ["sdist", "wheel"]},
        {"include": "extra_dir/**/*.py", "format": ["sdist", "wheel"]},
        {"include": "my_module.py", "format": ["sdist", "wheel"]},
        {"include": "package_with_include", "format": ["sdist", "wheel"]},
        {"include": "tests", "format": ["sdist"]},
        {"include": "for_wheel_only", "format": ["wheel"]},
        {"include": "src_package", "from": "src", "format": ["sdist", "wheel"]},
    ]

    assert package.include in (
        # with https://github.com/python-poetry/poetry-core/pull/773
        [
            {"path": "extra_dir/vcs_excluded.txt", "format": ["sdist", "wheel"]},
            {"path": "notes.txt", "format": ["sdist"]},
        ],
        # without https://github.com/python-poetry/poetry-core/pull/773
        [
            {"path": "extra_dir/vcs_excluded.txt", "format": ["sdist"]},
            {"path": "notes.txt", "format": ["sdist"]},
        ],
    )


def test_create_poetry_with_multi_constraints_dependency(
    fixture_dir: FixtureDirGetter,
) -> None:
    poetry = Factory().create_poetry(
        fixture_dir("project_with_multi_constraints_dependency")
    )

    package = poetry.package

    assert len(package.requires) == 2


def test_create_poetry_non_package_mode(fixture_dir: FixtureDirGetter) -> None:
    poetry = Factory().create_poetry(fixture_dir("non_package_mode"))

    assert not poetry.is_package_mode


def test_create_poetry_version_ok(fixture_dir: FixtureDirGetter) -> None:
    io = BufferedIO()
    Factory().create_poetry(fixture_dir("self_version_ok"), io=io)

    assert io.fetch_output() == ""
    assert io.fetch_error() == ""


def test_create_poetry_version_not_ok(fixture_dir: FixtureDirGetter) -> None:
    with pytest.raises(PoetryError) as e:
        Factory().create_poetry(fixture_dir("self_version_not_ok"))
    assert (
        str(e.value)
        == f"This project requires Poetry <1.2, but you are using Poetry {__version__}"
    )


@pytest.mark.parametrize(
    "project",
    ("with_primary_source_implicit", "with_primary_source_explicit"),
)
def test_poetry_with_primary_source(
    project: str, fixture_dir: FixtureDirGetter, with_simple_keyring: None
) -> None:
    io = BufferedIO()
    poetry = Factory().create_poetry(fixture_dir(project), io=io)

    assert not poetry.pool.has_repository("PyPI")
    assert poetry.pool.has_repository("foo")
    assert poetry.pool.get_priority("foo") is Priority.PRIMARY
    assert isinstance(poetry.pool.repository("foo"), LegacyRepository)
    assert {repo.name for repo in poetry.pool.repositories} == {"foo"}


def test_poetry_with_multiple_supplemental_sources(
    fixture_dir: FixtureDirGetter, with_simple_keyring: None
) -> None:
    poetry = Factory().create_poetry(fixture_dir("with_multiple_supplemental_sources"))

    assert poetry.pool.has_repository("PyPI")
    assert isinstance(poetry.pool.repository("PyPI"), PyPiRepository)
    assert poetry.pool.get_priority("PyPI") is Priority.PRIMARY
    assert poetry.pool.has_repository("foo")
    assert isinstance(poetry.pool.repository("foo"), LegacyRepository)
    assert poetry.pool.has_repository("bar")
    assert isinstance(poetry.pool.repository("bar"), LegacyRepository)
    assert {repo.name for repo in poetry.pool.repositories} == {"PyPI", "foo", "bar"}


def test_poetry_with_multiple_sources(
    fixture_dir: FixtureDirGetter, with_simple_keyring: None
) -> None:
    poetry = Factory().create_poetry(fixture_dir("with_multiple_sources"))

    assert not poetry.pool.has_repository("PyPI")
    assert poetry.pool.has_repository("bar")
    assert isinstance(poetry.pool.repository("bar"), LegacyRepository)
    assert poetry.pool.has_repository("foo")
    assert isinstance(poetry.pool.repository("foo"), LegacyRepository)
    assert {repo.name for repo in poetry.pool.repositories} == {"bar", "foo"}


def test_poetry_with_multiple_sources_pypi(
    fixture_dir: FixtureDirGetter, with_simple_keyring: None
) -> None:
    io = BufferedIO()
    poetry = Factory().create_poetry(fixture_dir("with_multiple_sources_pypi"), io=io)

    assert len(poetry.pool.repositories) == 4
    assert poetry.pool.has_repository("PyPI")
    assert isinstance(poetry.pool.repository("PyPI"), PyPiRepository)
    assert poetry.pool.get_priority("PyPI") is Priority.PRIMARY
    # PyPI must be between bar and baz!
    expected = ["bar", "PyPI", "baz", "foo"]
    assert [repo.name for repo in poetry.pool.repositories] == expected


def test_poetry_with_no_default_source(fixture_dir: FixtureDirGetter) -> None:
    poetry = Factory().create_poetry(fixture_dir("sample_project"))

    assert poetry.pool.has_repository("PyPI")
    assert poetry.pool.get_priority("PyPI") is Priority.PRIMARY
    assert isinstance(poetry.pool.repository("PyPI"), PyPiRepository)
    assert {repo.name for repo in poetry.pool.repositories} == {"PyPI"}


def test_poetry_with_supplemental_source(
    fixture_dir: FixtureDirGetter, with_simple_keyring: None
) -> None:
    io = BufferedIO()
    poetry = Factory().create_poetry(fixture_dir("with_supplemental_source"), io=io)

    assert poetry.pool.has_repository("PyPI")
    assert poetry.pool.get_priority("PyPI") is Priority.PRIMARY
    assert isinstance(poetry.pool.repository("PyPI"), PyPiRepository)
    assert poetry.pool.has_repository("supplemental")
    assert poetry.pool.get_priority("supplemental") is Priority.SUPPLEMENTAL
    assert isinstance(poetry.pool.repository("supplemental"), LegacyRepository)
    assert {repo.name for repo in poetry.pool.repositories} == {"PyPI", "supplemental"}
    assert io.fetch_error() == ""


def test_poetry_with_explicit_source(
    fixture_dir: FixtureDirGetter, with_simple_keyring: None
) -> None:
    io = BufferedIO()
    poetry = Factory().create_poetry(fixture_dir("with_explicit_source"), io=io)

    assert len(poetry.pool.repositories) == 1
    assert len(poetry.pool.all_repositories) == 2
    assert poetry.pool.has_repository("PyPI")
    assert poetry.pool.get_priority("PyPI") is Priority.PRIMARY
    assert isinstance(poetry.pool.repository("PyPI"), PyPiRepository)
    assert poetry.pool.has_repository("explicit")
    assert isinstance(poetry.pool.repository("explicit"), LegacyRepository)
    assert {repo.name for repo in poetry.pool.repositories} == {"PyPI"}
    assert io.fetch_error() == ""


def test_poetry_with_explicit_pypi_and_other(
    fixture_dir: FixtureDirGetter, with_simple_keyring: None
) -> None:
    io = BufferedIO()
    poetry = Factory().create_poetry(fixture_dir("with_explicit_pypi_and_other"), io=io)

    assert len(poetry.pool.repositories) == 1
    assert len(poetry.pool.all_repositories) == 2
    error = io.fetch_error()
    assert error == ""


@pytest.mark.parametrize(
    "project", ["with_explicit_pypi_no_other", "with_explicit_pypi_and_other_explicit"]
)
def test_poetry_with_pypi_explicit_only(
    project: str, fixture_dir: FixtureDirGetter, with_simple_keyring: None
) -> None:
    with pytest.raises(PoetryError) as e:
        Factory().create_poetry(fixture_dir(project))
    assert str(e.value) == "At least one source must not be configured as 'explicit'."


def test_validate(fixture_dir: FixtureDirGetter) -> None:
    complete = TOMLFile(fixture_dir("complete.toml"))
    pyproject: dict[str, Any] = complete.read()

    assert Factory.validate(pyproject) == {"errors": [], "warnings": []}


def test_validate_fails(fixture_dir: FixtureDirGetter) -> None:
    complete = TOMLFile(fixture_dir("complete.toml"))
    pyproject: dict[str, Any] = complete.read()
    pyproject["tool"]["poetry"]["this key is not in the schema"] = ""
    pyproject["tool"]["poetry"]["source"] = {}

    expected = [
        "tool.poetry.source must be array",
        (
            "Additional properties are not allowed "
            "('this key is not in the schema' was unexpected)"
        ),
    ]

    assert Factory.validate(pyproject) == {"errors": expected, "warnings": []}


def test_create_poetry_fails_on_invalid_configuration(
    fixture_dir: FixtureDirGetter,
) -> None:
    with pytest.raises(RuntimeError) as e:
        Factory().create_poetry(fixture_dir("invalid_pyproject_dep_name"))

    expected = """\
The Poetry configuration is invalid:
  - Project name (invalid) is same as one of its dependencies
"""

    assert str(e.value) == expected


def test_create_poetry_fails_on_nameless_project(
    fixture_dir: FixtureDirGetter,
) -> None:
    with pytest.raises(RuntimeError) as e:
        Factory().create_poetry(fixture_dir("nameless_pyproject"))

    expected = """\
The Poetry configuration is invalid:
  - Either [project.name] or [tool.poetry.name] is required in package mode.
"""

    assert str(e.value) == expected


def test_create_poetry_with_local_config(fixture_dir: FixtureDirGetter) -> None:
    poetry = Factory().create_poetry(fixture_dir("with_local_config"))

    assert not poetry.config.get("virtualenvs.in-project")
    assert not poetry.config.get("virtualenvs.create")
    assert not poetry.config.get("virtualenvs.options.always-copy")
    assert not poetry.config.get("virtualenvs.options.no-pip")
    assert not poetry.config.get("virtualenvs.options.system-site-packages")


def test_create_poetry_with_plugins(
    mocker: MockerFixture, fixture_dir: FixtureDirGetter
) -> None:
    mock_metadata_entry_points(mocker, MyPlugin)

    poetry = Factory().create_poetry(fixture_dir("sample_project"))

    assert poetry.package.readmes == (Path("README.md"),)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ({}, "Missing [name] in source."),
        ({"name": "foo"}, "Missing [url] in source 'foo'."),
        (
            {"name": "PyPI", "url": "https://example.com"},
            "The PyPI repository cannot be configured with a custom url.",
        ),
    ],
)
def test_create_package_source_invalid(
    source: dict[str, str],
    expected: str,
    config: Config,
    fixture_dir: FixtureDirGetter,
) -> None:
    with pytest.raises(InvalidSourceError) as e:
        Factory.create_package_source(source, config=config)
        Factory().create_poetry(fixture_dir("with_source_pypi_url"))

    assert str(e.value) == expected
