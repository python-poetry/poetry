import pytest

from poetry.packages import FileDependency
from poetry.utils._compat import Path

DIST_PATH = Path(__file__).parent.parent / "fixtures" / "distributions"


def test_file_dependency_wrong_path():
    with pytest.raises(ValueError):
        FileDependency("demo", DIST_PATH / "demo-0.2.0.tar.gz")


def test_file_dependency_dir():
    with pytest.raises(ValueError):
        FileDependency("demo", DIST_PATH)
