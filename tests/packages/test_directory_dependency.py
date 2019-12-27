from subprocess import CalledProcessError

import pytest

from poetry.packages.directory_dependency import DirectoryDependency
from poetry.utils._compat import Path
from poetry.utils.env import EnvCommandError
from poetry.utils.env import MockEnv as BaseMockEnv


fixtures_dir = Path(__file__).parent.parent / "fixtures"
DIST_PATH = Path(__file__).parent.parent / "fixtures" / "git" / "github.com" / "demo"


class MockEnv(BaseMockEnv):
    def run(self, bin, *args):
        raise EnvCommandError(CalledProcessError(1, "python", output=""))


def test_directory_dependency():
    dependency = DirectoryDependency("simple_project", fixtures_dir / "simple_project")

    assert dependency.pretty_name == "simple_project"
    assert dependency.develop
    assert dependency.path == fixtures_dir / "simple_project"
    assert dependency.base_pep_508_name == "simple_project @ {}".format(
        fixtures_dir / "simple_project"
    )


def test_directory_dependency_must_exist():
    with pytest.raises(ValueError):
        DirectoryDependency("demo", DIST_PATH / "invalid")
