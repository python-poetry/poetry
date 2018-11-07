import pytest

from poetry.io import NullIO
from poetry.packages import ProjectPackage
from poetry.packages.vcs_dependency import VCSDependency
from poetry.puzzle.provider import Provider
from poetry.repositories.pool import Pool
from poetry.repositories.repository import Repository
from poetry.utils._compat import PY35
from poetry.utils.env import EnvCommandError
from poetry.utils.env import MockEnv as BaseMockEnv

from tests.helpers import get_dependency

from subprocess import CalledProcessError


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


def test_search_for_vcs_setup_egg_info(provider):
    dependency = VCSDependency("demo", "git", "https://github.com/demo/demo.git")

    package = provider.search_for_vcs(dependency)[0]

    assert package.name == "demo"
    assert package.version.text == "0.1.2"
    assert package.requires == [
        get_dependency("pendulum", ">=1.4.4"),
        get_dependency("cleo", optional=True),
    ]
    assert package.extras == {"foo": [get_dependency("cleo")]}


@pytest.mark.skipif(not PY35, reason="AST parsing does not work for Python <3.4")
def test_search_for_vcs_read_setup(provider, mocker):
    mocker.patch("poetry.utils.env.Env.get", return_value=MockEnv())

    dependency = VCSDependency("demo", "git", "https://github.com/demo/demo.git")

    package = provider.search_for_vcs(dependency)[0]

    assert package.name == "demo"
    assert package.version.text == "0.1.2"
    assert package.requires == [
        get_dependency("pendulum", ">=1.4.4"),
        get_dependency("cleo", optional=True),
    ]
    assert package.extras == {"foo": [get_dependency("cleo")]}


def test_search_for_vcs_read_setup_raises_error_if_no_version(provider, mocker):
    mocker.patch("poetry.utils.env.Env.get", return_value=MockEnv())

    dependency = VCSDependency("demo", "git", "https://github.com/demo/no-version.git")

    with pytest.raises(RuntimeError):
        provider.search_for_vcs(dependency)
