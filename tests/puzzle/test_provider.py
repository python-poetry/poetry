from pathlib import Path
from subprocess import CalledProcessError

import pytest

from cleo.io.null_io import NullIO

from poetry.core.packages.directory_dependency import DirectoryDependency
from poetry.core.packages.file_dependency import FileDependency
from poetry.core.packages.project_package import ProjectPackage
from poetry.core.packages.vcs_dependency import VCSDependency
from poetry.inspection.info import PackageInfo
from poetry.puzzle.provider import Provider
from poetry.repositories.pool import Pool
from poetry.repositories.repository import Repository
from poetry.utils.env import EnvCommandError
from poetry.utils.env import MockEnv as BaseMockEnv
from tests.helpers import get_dependency


class MockEnv(BaseMockEnv):
    def run(self, bin, *args):
        raise EnvCommandError(CalledProcessError(1, "python", output=""))


@pytest.fixture
def root():
    return ProjectPackage("root", "1.2.3")


@pytest.fixture
def repository():
    return Repository()


@pytest.fixture
def pool(repository):
    pool = Pool()
    pool.add_repository(repository)

    return pool


@pytest.fixture
def provider(root, pool):
    return Provider(root, pool, NullIO())


@pytest.mark.parametrize("value", [True, False])
def test_search_for_vcs_retains_develop_flag(provider, value):
    dependency = VCSDependency(
        "demo", "git", "https://github.com/demo/demo.git", develop=value
    )
    package = provider.search_for_vcs(dependency)[0]
    assert package.develop == value


def test_search_for_vcs_setup_egg_info(provider):
    dependency = VCSDependency("demo", "git", "https://github.com/demo/demo.git")

    package = provider.search_for_vcs(dependency)[0]

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


def test_search_for_vcs_setup_egg_info_with_extras(provider):
    dependency = VCSDependency(
        "demo", "git", "https://github.com/demo/demo.git", extras=["foo"]
    )

    package = provider.search_for_vcs(dependency)[0]

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


def test_search_for_vcs_read_setup(provider, mocker):
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=MockEnv())

    dependency = VCSDependency("demo", "git", "https://github.com/demo/demo.git")

    package = provider.search_for_vcs(dependency)[0]

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


def test_search_for_vcs_read_setup_with_extras(provider, mocker):
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=MockEnv())

    dependency = VCSDependency(
        "demo", "git", "https://github.com/demo/demo.git", extras=["foo"]
    )

    package = provider.search_for_vcs(dependency)[0]

    assert package.name == "demo"
    assert package.version.text == "0.1.2"

    required = [r for r in package.requires if not r.is_optional()]
    optional = [r for r in package.requires if r.is_optional()]
    assert required == [get_dependency("pendulum", ">=1.4.4")]
    assert optional == [get_dependency("tomlkit"), get_dependency("cleo")]


def test_search_for_vcs_read_setup_raises_error_if_no_version(provider, mocker):
    mocker.patch(
        "poetry.inspection.info.PackageInfo._pep517_metadata",
        return_value=PackageInfo(name="demo", version=None),
    )

    dependency = VCSDependency("demo", "git", "https://github.com/demo/no-version.git")

    with pytest.raises(RuntimeError):
        provider.search_for_vcs(dependency)


@pytest.mark.parametrize("directory", ["demo", "non-canonical-name"])
def test_search_for_directory_setup_egg_info(provider, directory):
    dependency = DirectoryDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "git"
        / "github.com"
        / "demo"
        / directory,
    )

    package = provider.search_for_directory(dependency)[0]

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


def test_search_for_directory_setup_egg_info_with_extras(provider):
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

    package = provider.search_for_directory(dependency)[0]

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
def test_search_for_directory_setup_with_base(provider, directory):
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

    package = provider.search_for_directory(dependency)[0]

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


def test_search_for_directory_setup_read_setup(provider, mocker):
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

    package = provider.search_for_directory(dependency)[0]

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


def test_search_for_directory_setup_read_setup_with_extras(provider, mocker):
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

    package = provider.search_for_directory(dependency)[0]

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


def test_search_for_directory_setup_read_setup_with_no_dependencies(provider):
    dependency = DirectoryDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "git"
        / "github.com"
        / "demo"
        / "no-dependencies",
    )

    package = provider.search_for_directory(dependency)[0]

    assert package.name == "demo"
    assert package.version.text == "0.1.2"
    assert package.requires == []
    assert package.extras == {}


def test_search_for_directory_poetry(provider):
    dependency = DirectoryDependency(
        "project-with-extras",
        Path(__file__).parent.parent / "fixtures" / "project_with_extras",
    )

    package = provider.search_for_directory(dependency)[0]

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


def test_search_for_directory_poetry_with_extras(provider):
    dependency = DirectoryDependency(
        "project-with-extras",
        Path(__file__).parent.parent / "fixtures" / "project_with_extras",
        extras=["extras_a"],
    )

    package = provider.search_for_directory(dependency)[0]

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


def test_search_for_file_sdist(provider):
    dependency = FileDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "distributions"
        / "demo-0.1.0.tar.gz",
    )

    package = provider.search_for_file(dependency)[0]

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


def test_search_for_file_sdist_with_extras(provider):
    dependency = FileDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "distributions"
        / "demo-0.1.0.tar.gz",
        extras=["foo"],
    )

    package = provider.search_for_file(dependency)[0]

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


def test_search_for_file_wheel(provider):
    dependency = FileDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "distributions"
        / "demo-0.1.0-py2.py3-none-any.whl",
    )

    package = provider.search_for_file(dependency)[0]

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


def test_search_for_file_wheel_with_extras(provider):
    dependency = FileDependency(
        "demo",
        Path(__file__).parent.parent
        / "fixtures"
        / "distributions"
        / "demo-0.1.0-py2.py3-none-any.whl",
        extras=["foo"],
    )

    package = provider.search_for_file(dependency)[0]

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
