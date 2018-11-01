import pytest

from poetry.packages.directory_dependency import DirectoryDependency
from poetry.utils._compat import PY35
from poetry.utils._compat import Path
from poetry.utils.env import EnvCommandError
from poetry.utils.env import MockEnv as BaseMockEnv

from subprocess import CalledProcessError


class MockEnv(BaseMockEnv):
    def run(self, bin, *args):
        raise EnvCommandError(CalledProcessError(1, "python", output=""))


DIST_PATH = Path(__file__).parent.parent / "fixtures" / "git" / "github.com" / "demo"


def test_directory_dependency_egg_info():
    dependency = DirectoryDependency(DIST_PATH / "demo")

    assert dependency.is_directory()
    assert dependency.name == "demo"
    assert dependency.pretty_constraint == "0.1.2"
    assert dependency.python_versions == "*"

    package = dependency.package
    assert package.name == "demo"
    assert package.pretty_version == "0.1.2"
    assert package.python_versions == "*"


@pytest.mark.skipif(not PY35, reason="AST parsing does not work for Python <3.4")
def test_directory_dependency_no_egg_info(mocker):
    mocker.patch("poetry.utils.env.Env.get", return_value=MockEnv())

    dependency = DirectoryDependency(DIST_PATH / "demo")

    assert dependency.is_directory()
    assert dependency.name == "demo"
    assert dependency.pretty_constraint == "0.1.2"
    assert dependency.python_versions == "*"

    package = dependency.package
    assert package.name == "demo"
    assert package.pretty_version == "0.1.2"
    assert package.python_versions == "*"


def test_directory_dependency_with_no_version_should_raise_an_error(mocker):
    mocker.patch("poetry.utils.env.Env.get", return_value=MockEnv())

    with pytest.raises(RuntimeError):
        DirectoryDependency(DIST_PATH / "no-version")
