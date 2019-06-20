import random

import pytest
import semver

from poetry.semver.semver_utils import is_semver
from poetry.semver.semver_utils import sorted_semver

# semver sorted values, from
# https://github.com/k-bx/python-semver/blob/master/test_semver.py
SORTED = [
    "1.0.0-alpha",
    "1.0.0-alpha.1",
    "1.0.0-alpha.beta",
    "1.0.0-beta",
    "1.0.0-beta.2",
    "1.0.0-beta.11",
    "1.0.0-rc.1",
    "1.0.0",
    "1.0.0",
    "2.0.0",
]


@pytest.mark.parametrize(
    "version,result",
    [
        ("1.2.3-alpha.1.2+build.11.e0f985a", True),
        ("2.0.0", True),
        ("1.0.0", True),
        ("1.0.0-alpha.1", True),
        ("1.0.0-alpha", True),
        ("1.0.0-alpha.beta", True),
        ("1.0.0-rc.1", True),
        ("1.0.0-beta.11", True),
        ("1.0.0-beta.2", True),
        ("1.0.0-beta", True),
        ("1.0.0.2", False),
        ("1.0.0.0rc2", False),
        ("n.a.n", False),
        ("hot-fix-666", False),
    ],
)
def test_is_semver(mocker, version, result):
    # The semver library is responsible for testing all variants, so this
    # test simply passes some examples and checks that semver.parse is called;
    # See also https://github.com/k-bx/python-semver/blob/master/test_semver.py
    parser = mocker.spy(semver.VersionInfo, name="parse")
    assert is_semver(version) == result
    assert parser.call_count == 1


@pytest.mark.parametrize(
    "unsorted, sorted_",
    [
        (random.sample(SORTED, k=len(SORTED)), SORTED),
        (["1.0.3", "1.0.2", "1.0.1"], ["1.0.1", "1.0.2", "1.0.3"]),
        (
            ["1.0.3", "1.0.2", "1.0.1", "n.a.n", "hot-fix-666"],
            ["1.0.1", "1.0.2", "1.0.3"],
        ),
        (["10.0.3", "1.0.3", "n.a.n", "hot-fix-666"], ["1.0.3", "10.0.3"]),
    ],
)
def test_sem_ver_sorted(mocker, unsorted, sorted_):
    parser = mocker.spy(semver.VersionInfo, name="parse")
    assert sorted_semver(unsorted) == sorted_
    # parse is called to (a) check is_semver and (b) instantiate semver.VersionInfo for sort key
    assert parser.call_count == (len(unsorted) + len(sorted_))
    # test the reverse order
    parser.reset_mock()
    assert sorted_semver(unsorted, reverse=True) == list(reversed(sorted_))
    assert parser.call_count == (len(unsorted) + len(sorted_))
