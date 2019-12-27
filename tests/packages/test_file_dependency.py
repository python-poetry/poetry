import pytest

from poetry.packages import FileDependency
from poetry.utils._compat import Path


DIST_PATH = Path(__file__).parent.parent / "fixtures" / "distributions"


def test_file_dependency():
    dependency = FileDependency("demo", DIST_PATH / "demo-0.1.0.tar.gz")

    assert dependency.pretty_name == "demo"
    assert dependency.path == DIST_PATH / "demo-0.1.0.tar.gz"
    assert dependency.base_pep_508_name == "demo @ {}".format(
        DIST_PATH / "demo-0.1.0.tar.gz"
    )


def test_file_dependency_wrong_path():
    with pytest.raises(ValueError):
        FileDependency("demo", DIST_PATH / "demo-0.2.0.tar.gz")


def test_file_dependency_dir():
    with pytest.raises(ValueError):
        FileDependency("demo", DIST_PATH)
