import random

import pytest

import poetry.semver
from poetry.semver.version_utils import is_version
from poetry.semver.version_utils import sorted_versions

# semver sorted values, from
# https://github.com/k-bx/python-semver/blob/master/test_semver.py
SORTED_SEMVER = [
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

# current poetry behavior
# - may not actually be PEP-0440
# - depends on Version sort-behavior in this current implementation
SORTED_VERSIONS = [
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

UNSORTED_VERSIONS = [
    "1.0.0-alpha.beta",
    "1.0.0-alpha",
    "1.0.0-beta.2",
    "1.0.0-alpha.1",
    "1.0.0-beta.11",
    "1.0.0-rc.1",
    "2.0.0",
    "1.0.0",
    "1.0.0-beta",
    "1.0.0",
]


# versions compatible with both PEP-0440 and SEM-VER
@pytest.mark.parametrize(
    "any_version,result",
    [("2.0.0", True), ("1.0.0", True), ("n.a.n", False), ("hot-fix-666", False)],
)
def test_is_version(mocker, any_version, result):
    parser = mocker.spy(poetry.semver.version.Version, name="parse")
    assert is_version(any_version) == result
    assert parser.call_count == 1


# versions compatible with SEM-VER, excluded by PEP-0440
# - uncomment parameters for TDD red->green
# - TODO: add SEM-VER option to Version.parse? (or sub-class)
@pytest.mark.parametrize(
    "sem_version,result",
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
        # ("1.0.0.2", False),     # PEP-0440 OK, sem-ver not
        # ("1.0.0.0rc2", False),  # PEP-0440 OK, sem-ver not
        ("n.a.n", False),
        ("hot-fix-666", False),
    ],
)
def test_semver_is_version(mocker, sem_version, result):
    parser = mocker.spy(poetry.semver.version.Version, name="parse")
    assert is_version(sem_version) == result
    assert parser.call_count == 1


# versions compatible with PEP-0440, excluded by SEM-VER
# - uncomment parameters for TDD red->green
# - TODO: add PEP-0440 option to Version.parse? (or sub-class)
@pytest.mark.parametrize(
    "pep0440_version,result",
    [
        # ("1.2.3-alpha.1.2+build.11.e0f985a", False),
        ("2.0.0", True),
        ("1.0.0", True),
        # ("1.0.0-alpha.1", False),
        # ("1.0.0-alpha", False),
        # ("1.0.0-alpha.beta", False),
        # ("1.0.0-rc.1", False),
        # ("1.0.0-beta.11", False),
        # ("1.0.0-beta.2", False),
        # ("1.0.0-beta", False),
        ("1.0.0.2", True),  # PEP-0440 OK, sem-ver not
        ("1.0.0.0rc2", True),  # PEP-0440 OK, sem-ver not
        ("n.a.n", False),
        ("hot-fix-666", False),
    ],
)
def test_pep0440_is_version(mocker, pep0440_version, result):
    parser = mocker.spy(poetry.semver.version.Version, name="parse")
    assert is_version(pep0440_version) == result
    assert parser.call_count == 1


@pytest.mark.parametrize(
    "unsorted, sorted_",
    [
        # (UNSORTED_VERSIONS, SORTED_VERSIONS),  # fails - TODO: fix it?
        (["1.0.3", "1.0.2", "1.0.1"], ["1.0.1", "1.0.2", "1.0.3"]),
        (
            ["1.0.3", "1.0.2", "1.0.1", "n.a.n", "hot-fix-666"],
            ["1.0.1", "1.0.2", "1.0.3"],
        ),
        (["10.0.3", "1.0.3", "n.a.n", "hot-fix-666"], ["1.0.3", "10.0.3"]),
    ],
)
def test_sorted_versions(mocker, unsorted, sorted_):
    parser = mocker.spy(poetry.semver.version_utils.Version, name="parse")
    assert sorted_versions(unsorted) == sorted_
    # parser is called to (a) check is_version and (b) instantiate Version for sort key
    assert parser.call_count == (len(unsorted) + len(sorted_))
    # test the reverse order
    parser.reset_mock()
    assert sorted_versions(unsorted, reverse=True) == list(reversed(sorted_))
    assert parser.call_count == (len(unsorted) + len(sorted_))
