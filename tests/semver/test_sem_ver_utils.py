import pytest

import poetry.semver
from poetry.semver import is_sem_ver_constraint
from poetry.semver import sem_ver_sorted


@pytest.mark.parametrize(
    "constraint,result",
    [
        ("*", True),
        ("*.*", True),
        ("v*.*", True),
        ("*.x.*", True),
        ("x.X.x.*", True),
        ("!=1.0.0", True),
        (">1.0.0", True),
        ("<1.2.3", True),
        ("<=1.2.3", True),
        (">=1.2.3", True),
        ("=1.2.3", True),
        ("1.2.3", True),
        ("=1.0", True),
        ("1.2.3b5", True),
        (">= 1.2.3", True),
        (">dev", True),
        ("hot-fix-666", False),
    ],
)
def test_is_sem_ver_constraint(mocker, constraint, result):
    parser = mocker.spy(poetry.semver, name="parse_single_constraint")
    assert is_sem_ver_constraint(constraint) == result
    assert parser.call_count == 1


@pytest.mark.parametrize(
    "unsorted, sorted_",
    [
        (["1.0.3", "1.0.2", "1.0.1"], ["1.0.1", "1.0.2", "1.0.3"]),
        (["1.0.0.2", "1.0.0.0rc2"], ["1.0.0.0rc2", "1.0.0.2"]),
        (["1.0.0.0", "1.0.0.0rc2"], ["1.0.0.0rc2", "1.0.0.0"]),
        (["1.0.0.0.0", "1.0.0.0rc2"], ["1.0.0.0rc2", "1.0.0.0.0"]),
        (["1.0.0rc2", "1.0.0rc1"], ["1.0.0rc1", "1.0.0rc2"]),
        (["1.0.0rc2", "1.0.0b1"], ["1.0.0b1", "1.0.0rc2"]),
        (["1.0.3", "1.0.2", "1.0.1", "hot-fix-666"], ["1.0.1", "1.0.2", "1.0.3"]),
        (["10.0.3", "1.0.3", "hot-fix-666"], ["1.0.3", "10.0.3"]),
    ],
)
def test_sem_ver_sorted(mocker, unsorted, sorted_):
    parser = mocker.spy(poetry.semver, name="parse_single_constraint")
    assert sem_ver_sorted(unsorted) == sorted_
    assert parser.call_count == len(sorted_)
