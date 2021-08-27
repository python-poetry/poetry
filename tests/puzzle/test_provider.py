from pathlib import Path
from subprocess import CalledProcessError
<<<<<<< HEAD
from typing import TYPE_CHECKING
=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

import pytest

from cleo.io.null_io import NullIO
<<<<<<< HEAD
=======

>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
from poetry.core.packages.directory_dependency import DirectoryDependency
from poetry.core.packages.file_dependency import FileDependency
from poetry.core.packages.project_package import ProjectPackage
from poetry.core.packages.vcs_dependency import VCSDependency
<<<<<<< HEAD

=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
from poetry.inspection.info import PackageInfo
from poetry.puzzle.provider import Provider
from poetry.repositories.pool import Pool
from poetry.repositories.repository import Repository
from poetry.utils.env import EnvCommandError
from poetry.utils.env import MockEnv as BaseMockEnv
from tests.helpers import get_dependency


<<<<<<< HEAD
if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class MockEnv(BaseMockEnv):
    def run(self, bin: str, *args: str) -> None:
=======
class MockEnv(BaseMockEnv):
    def run(self, bin, *args):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        raise EnvCommandError(CalledProcessError(1, "python", output=""))


@pytest.fixture
<<<<<<< HEAD
def root() -> ProjectPackage:
=======
def root():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return ProjectPackage("root", "1.2.3")


@pytest.fixture
<<<<<<< HEAD
def repository() -> Repository:
=======
def repository():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return Repository()


@pytest.fixture
<<<<<<< HEAD
def pool(repository: Repository) -> Pool:
=======
def pool(repository):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    pool = Pool()
    pool.add_repository(repository)

    return pool


@pytest.fixture
<<<<<<< HEAD
def provider(root: ProjectPackage, pool: Pool) -> Provider:
=======
def provider(root, pool):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return Provider(root, pool, NullIO())


@pytest.mark.parametrize("value", [True, False])
<<<<<<< HEAD
def test_search_for_vcs_retains_develop_flag(provider: Provider, value: bool):
=======
def test_search_for_vcs_retains_develop_flag(provider, value):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    dependency = VCSDependency(
        "demo", "git", "https://github.com/demo/demo.git", develop=value
    )
    package = provider.search_for_vcs(dependency)[0]
    assert package.develop == value


<<<<<<< HEAD
def test_search_for_vcs_setup_egg_info(provider: Provider):
=======
def test_search_for_vcs_setup_egg_info(provider):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_search_for_vcs_setup_egg_info_with_extras(provider: Provider):
=======
def test_search_for_vcs_setup_egg_info_with_extras(provider):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_search_for_vcs_read_setup(provider: Provider, mocker: "MockerFixture"):
=======
def test_search_for_vcs_read_setup(provider, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_search_for_vcs_read_setup_with_extras(
    provider: Provider, mocker: "MockerFixture"
):
=======
def test_search_for_vcs_read_setup_with_extras(provider, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_search_for_vcs_read_setup_raises_error_if_no_version(
    provider: Provider, mocker: "MockerFixture"
):
=======
def test_search_for_vcs_read_setup_raises_error_if_no_version(provider, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    mocker.patch(
        "poetry.inspection.info.PackageInfo._pep517_metadata",
        return_value=PackageInfo(name="demo", version=None),
    )

    dependency = VCSDependency("demo", "git", "https://github.com/demo/no-version.git")

    with pytest.raises(RuntimeError):
        provider.search_for_vcs(dependency)


@pytest.mark.parametrize("directory", ["demo", "non-canonical-name"])
<<<<<<< HEAD
def test_search_for_directory_setup_egg_info(provider: Provider, directory: str):
=======
def test_search_for_directory_setup_egg_info(provider, directory):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_search_for_directory_setup_egg_info_with_extras(provider: Provider):
=======
def test_search_for_directory_setup_egg_info_with_extras(provider):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
<<<<<<< HEAD
def test_search_for_directory_setup_with_base(provider: Provider, directory: str):
=======
def test_search_for_directory_setup_with_base(provider, directory):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_search_for_directory_setup_read_setup(
    provider: Provider, mocker: "MockerFixture"
):
=======
def test_search_for_directory_setup_read_setup(provider, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_search_for_directory_setup_read_setup_with_extras(
    provider: Provider, mocker: "MockerFixture"
):
=======
def test_search_for_directory_setup_read_setup_with_extras(provider, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_search_for_directory_setup_read_setup_with_no_dependencies(provider: Provider):
=======
def test_search_for_directory_setup_read_setup_with_no_dependencies(provider):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_search_for_directory_poetry(provider: Provider):
=======
def test_search_for_directory_poetry(provider):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_search_for_directory_poetry_with_extras(provider: Provider):
=======
def test_search_for_directory_poetry_with_extras(provider):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_search_for_file_sdist(provider: Provider):
=======
def test_search_for_file_sdist(provider):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_search_for_file_sdist_with_extras(provider: Provider):
=======
def test_search_for_file_sdist_with_extras(provider):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_search_for_file_wheel(provider: Provider):
=======
def test_search_for_file_wheel(provider):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_search_for_file_wheel_with_extras(provider: Provider):
=======
def test_search_for_file_wheel_with_extras(provider):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
