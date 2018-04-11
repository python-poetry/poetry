import pytest

from poetry.packages import FileDependency
from poetry.utils._compat import Path

DIST_PATH = Path(__file__).parent.parent / 'fixtures' / 'distributions'


def test_file_dependency_wheel():
    dependency = FileDependency(DIST_PATH / 'demo-0.1.0-py2.py3-none-any.whl')

    assert dependency.is_file()
    assert dependency.name == 'demo'
    assert dependency.pretty_constraint == '0.1.0'
    assert dependency.python_versions == '*'
    assert dependency.platform == '*'

    meta = dependency.metadata
    assert meta.requires_dist == [
        'pendulum (>=1.4.0.0,<2.0.0.0)'
    ]


def test_file_dependency_sdist():
    dependency = FileDependency(DIST_PATH / 'demo-0.1.0.tar.gz')

    assert dependency.is_file()
    assert dependency.name == 'demo'
    assert dependency.pretty_constraint == '0.1.0'
    assert dependency.python_versions == '*'
    assert dependency.platform == '*'

    meta = dependency.metadata
    assert meta.requires_dist == [
        'pendulum (>=1.4.0.0,<2.0.0.0)'
    ]


def test_file_dependency_wrong_path():
    with pytest.raises(ValueError):
        FileDependency(DIST_PATH / 'demo-0.2.0.tar.gz')


def test_file_dependency_dir():
    with pytest.raises(ValueError):
        FileDependency(DIST_PATH)
