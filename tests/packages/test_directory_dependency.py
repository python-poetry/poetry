import pytest

from poetry.packages.directory_dependency import DirectoryDependency
from poetry.utils._compat import Path
from poetry.utils.env import EnvCommandError
from poetry.utils.env import MockEnv as BaseMockEnv

from subprocess import CalledProcessError


class MockEnv(BaseMockEnv):
    def run(self, bin, *args):
        raise EnvCommandError(CalledProcessError(1, "python", output=""))


DIST_PATH = Path(__file__).parent.parent / "fixtures" / "git" / "github.com" / "demo"


def test_directory_dependency_must_exist():
    with pytest.raises(ValueError):
        DirectoryDependency("demo", DIST_PATH / "invalid")
