from __future__ import annotations

from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

import pytest

from cleo.io.null_io import NullIO
from poetry.core.packages.directory_dependency import DirectoryDependency
from poetry.core.packages.file_dependency import FileDependency
from poetry.core.packages.project_package import ProjectPackage
from poetry.core.packages.vcs_dependency import VCSDependency

from poetry.factory import Factory
from poetry.inspection.info import PackageInfo
from poetry.packages import DependencyPackage
from poetry.puzzle.provider import Provider
from poetry.repositories.pool import Pool
from poetry.repositories.repository import Repository
from poetry.utils.env import EnvCommandError
from poetry.utils.env import MockEnv as BaseMockEnv
from tests.helpers import get_dependency


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class MockEnv(BaseMockEnv):
    def run(self, bin: str, *args: str) -> None:
        raise EnvCommandError(CalledProcessError(1, "python", output=""))


@pytest.fixture
def root() -> ProjectPackage:
    return ProjectPackage("root", "1.2.3")


@pytest.fixture
def repository() -> Repository:
    return Repository()


@pytest.fixture
def pool(repository: Repository) -> Pool:
    pool = Pool()
    pool.add_repository(repository)

    return pool


@pytest.fixture
def provider(root: ProjectPackage, pool: Pool) -> Provider:
    return Provider(root, pool, NullIO())


@pytest.mark.parametrize("value", [True, False])
def test_search_for_vcs_retains_develop_flag(provider: Provider, value: bool):
    dependency = VCSDependency(
        "demo", "git", "https://github.com/demo/demo.git", develop=value
    )
    package = provider.search_for_direct_origin_dependency(dependency)
    assert package.develop == value


def test_search_for_vcs_setup_egg_info(provider: Provider):
    dependency = VCSDependency("demo", "git", "https://github.com/demo/demo.git")

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_vcs_setup_egg_info_with_extras(provider: Provider):
    dependency = VCSDependency(
        "demo", "git", "https://github.com/demo/demo.git", extras=["foo"]
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_vcs_read_setup(provider: Provider, mocker: MockerFixture):
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=MockEnv())

    dependency = VCSDependency("demo", "git", "https://github.com/demo/demo.git")

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_vcs_read_setup_with_extras(
    provider: Provider, mocker: MockerFixture
):
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=MockEnv())

    dependency = VCSDependency(
        "demo", "git", "https://github.com/demo/demo.git", extras=["foo"]
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]


def test_search_for_vcs_read_setup_raises_error_if_no_version(
    provider: Provider, mocker: MockerFixture
):
    mocker.patch(
        "poetry.inspection.info.get_pep517_metadata",
        return_value=PackageInfo(name="demo", version=None),
    )

    dependency = VCSDependency("demo", "git", "https://github.com/demo/no-version.git")

    with pytest.raises(RuntimeError):
        provider.search_for_direct_origin_dependency(dependency)


@pytest.mark.parametrize("directory", ["demo", "non-canonical-name"])
def test_search_for_directory_setup_egg_info(provider: Provider, directory: str):
    dependency = DirectoryDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "git"
        / "github.com"
        / "demo"
        / directory,
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_directory_setup_egg_info_with_extras(provider: Provider):
    dependency = DirectoryDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "git"
        / "github.com"
        / "demo"
        / "demo",
        extras=["foo"],
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


@pytest.mark.parametrize("directory", ["demo", "non-canonical-name"])
def test_search_for_directory_setup_with_base(provider: Provider, directory: str):
    dependency = DirectoryDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "git"
        / "github.com"
        / "demo"
        / directory,
        base=Path(__file__).parent.parent
        / "fixtures"
        / "git"
        / "github.com"
        / "demo"
        / directory,
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }
    assert package.root_dir == (
        Path(__file__).parent.parent
        / "fixtures"
        / "git"
        / "github.com"
        / "demo"
        / directory
    )


def test_search_for_directory_setup_read_setup(
    provider: Provider, mocker: MockerFixture
):
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=MockEnv())

    dependency = DirectoryDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "git"
        / "github.com"
        / "demo"
        / "demo",
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_directory_setup_read_setup_with_extras(
    provider: Provider, mocker: MockerFixture
):
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=MockEnv())

    dependency = DirectoryDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "git"
        / "github.com"
        / "demo"
        / "demo",
        extras=["foo"],
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_directory_setup_read_setup_with_no_dependencies(provider: Provider):
    dependency = DirectoryDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "git"
        / "github.com"
        / "demo"
        / "no-dependencies",
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.2"
    assert package.requires == []
    assert package.extras == {}


def test_search_for_directory_poetry(provider: Provider):
    dependency = DirectoryDependency(
        "project-with-extras",
        Path(__file__).parent.parent / "fixtures" / "project_with_extras",
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "project-with-extras"
    assert package.version.text == "1.2.3"

    required = [
        r for r in sorted(package.requires, key=lambda r: r.name) if not r.is_optional()
    ]
    optional = [
        r for r in sorted(package.requires, key=lambda r: r.name) if r.is_optional()
    ]
    assert required == []
    assert optional == [
        get_dependency("cachy", ">=0.2.0"),
        get_dependency("pendulum", ">=1.4.4"),
    ]
    assert package.extras == {
        "extras_a": [get_dependency("pendulum", ">=1.4.4")],
        "extras_b": [get_dependency("cachy", ">=0.2.0")],
    }


def test_search_for_directory_poetry_with_extras(provider: Provider):
    dependency = DirectoryDependency(
        "project-with-extras",
        Path(__file__).parent.parent / "fixtures" / "project_with_extras",
        extras=["extras_a"],
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "project-with-extras"
    assert package.version.text == "1.2.3"

    required = [
        r for r in sorted(package.requires, key=lambda r: r.name) if not r.is_optional()
    ]
    optional = [
        r for r in sorted(package.requires, key=lambda r: r.name) if r.is_optional()
    ]
    assert required == []
    assert optional == [
        get_dependency("cachy", ">=0.2.0"),
        get_dependency("pendulum", ">=1.4.4"),
    ]
    assert package.extras == {
        "extras_a": [get_dependency("pendulum", ">=1.4.4")],
        "extras_b": [get_dependency("cachy", ">=0.2.0")],
    }


def test_search_for_file_sdist(provider: Provider):
    dependency = FileDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "distributions"
        / "demo-0.1.0.tar.gz",
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.0"

    required = [
        r for r in sorted(package.requires, key=lambda r: r.name) if not r.is_optional()
    ]
    optional = [
        r for r in sorted(package.requires, key=lambda r: r.name) if r.is_optional()
    ]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [
        get_dependency("cleo"),
        get_dependency("tomlkit"),
    ]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_file_sdist_with_extras(provider: Provider):
    dependency = FileDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "distributions"
        / "demo-0.1.0.tar.gz",
        extras=["foo"],
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.0"

    required = [
        r for r in sorted(package.requires, key=lambda r: r.name) if not r.is_optional()
    ]
    optional = [
        r for r in sorted(package.requires, key=lambda r: r.name) if r.is_optional()
    ]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [
        get_dependency("cleo"),
        get_dependency("tomlkit"),
    ]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_file_wheel(provider: Provider):
    dependency = FileDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "distributions"
        / "demo-0.1.0-py2.py3-none-any.whl",
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.0"

    required = [
        r for r in sorted(package.requires, key=lambda r: r.name) if not r.is_optional()
    ]
    optional = [
        r for r in sorted(package.requires, key=lambda r: r.name) if r.is_optional()
    ]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [
        get_dependency("cleo"),
        get_dependency("tomlkit"),
    ]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_search_for_file_wheel_with_extras(provider: Provider):
    dependency = FileDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "distributions"
        / "demo-0.1.0-py2.py3-none-any.whl",
        extras=["foo"],
    )

    package = provider.search_for_direct_origin_dependency(dependency)

    assert package.name == "demo"
    assert package.version.text == "0.1.0"

    required = [
        r for r in sorted(package.requires, key=lambda r: r.name) if not r.is_optional()
    ]
    optional = [
        r for r in sorted(package.requires, key=lambda r: r.name) if r.is_optional()
    ]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [
        get_dependency("cleo"),
        get_dependency("tomlkit"),
    ]
    assert package.extras == {
        "foo": [get_dependency("cleo")],
        "bar": [get_dependency("tomlkit")],
    }


def test_complete_package_preserves_source_type(
    provider: Provider, root: ProjectPackage
) -> None:
    fixtures = Path(__file__).parent.parent / "fixtures"
    project_dir = fixtures.joinpath("with_conditional_path_deps")
    for folder in ["demo_one", "demo_two"]:
        path = (project_dir / folder).as_posix()
        root.add_dependency(Factory.create_dependency("demo", {"path": path}))

    complete_package = provider.complete_package(
        DependencyPackage(root.to_dependency(), root)
    )

    requires = complete_package.package.all_requires
    assert len(requires) == 2
    assert {requires[0].source_url, requires[1].source_url} == {
        project_dir.joinpath("demo_one").as_posix(),
        project_dir.joinpath("demo_two").as_posix(),
    }


def test_complete_package_preserves_source_type_with_subdirectories(
    provider: Provider, root: ProjectPackage
) -> None:
    dependency_one = Factory.create_dependency(
        "one",
        {
            "git": "https://github.com/demo/subdirectories.git",
            "subdirectory": "one",
        },
    )
    dependency_one_copy = Factory.create_dependency(
        "one",
        {
            "git": "https://github.com/demo/subdirectories.git",
            "subdirectory": "one-copy",
        },
    )
    dependency_two = Factory.create_dependency(
        "two",
        {"git": "https://github.com/demo/subdirectories.git", "subdirectory": "two"},
    )

    root.add_dependency(
        Factory.create_dependency(
            "one",
            {
                "git": "https://github.com/demo/subdirectories.git",
                "subdirectory": "one",
            },
        )
    )
    root.add_dependency(dependency_one_copy)
    root.add_dependency(dependency_two)

    complete_package = provider.complete_package(
        DependencyPackage(root.to_dependency(), root)
    )

    requires = complete_package.package.all_requires
    assert len(requires) == 3
    assert {r.to_pep_508() for r in requires} == {
        dependency_one.to_pep_508(),
        dependency_one_copy.to_pep_508(),
        dependency_two.to_pep_508(),
    }
