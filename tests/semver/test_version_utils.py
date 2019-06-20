import random

import pytest

import poetry.semver
from poetry.semver.version_utils import is_legacy_version
from poetry.semver.version_utils import is_pep440_version
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


# versions compatible with PEP-0440 (not legacy versions), excluded by SEM-VER
# the packaging.version implementation seems to interpret SEM-VER versions and
# cast them into a PEP-0440 form, e.g. "1.0.0-alpha.1" -> "1.0.0a1"
@pytest.mark.parametrize(
    "pep0440_version,result",
    [
        ("1.2.3-alpha.1.2+build.11.e0f985a", False),  # sem-ver / legacy
        ("2.0.0", True),  # all OK
        ("1.0.0", True),  # all OK
        ("1.0.0-alpha.1", True),  # sem-ver converted to PEP-0440 "1.0.0a1"
        ("1.0.0-alpha", True),  # sem-ver converted to PEP-0440 "1.0.0a0"
        ("1.0.0-alpha.beta", False),  # sem-ver / LegacyVersion
        ("1.0.0-rc.1", True),  # sem-ver converted to PEP-0440 "1.0.0rc1"
        ("1.0.0-beta.11", True),  # sem-ver converted to PEP-0440 "1.0.0b11"
        ("1.0.0-beta.2", True),  # sem-ver converted to PEP-0440 "1.0.0b2"
        ("1.0.0-beta", True),  # sem-ver converted to PEP-0440 "1.0.0b0"
        ("1.0.0.2", True),  # PEP-0440 OK, sem-ver not
        ("1.0.0.0rc2", True),  # PEP-0440 OK, sem-ver not
        ("n.a.n", False),  # LegacyVersion (huh?)
        ("hot-fix-666", False),  # LegacyVersion (huh?)
    ],
)
def test_is_pep0440_version(mocker, pep0440_version, result):
    parser = mocker.spy(poetry.semver.version_utils.pep440_version, name="parse")
    assert is_pep440_version(pep0440_version) == result
    assert parser.call_count == 1


# legacy versions (incompatible with PEP-0440) - ? relationship to SEM-VER
@pytest.mark.parametrize(
    "legacy_version,result",
    [
        ("1.2.3-alpha.1.2+build.11.e0f985a", True),  # sem-ver / legacy
        ("2.0.0", False),  # all OK
        ("1.0.0", False),  # all OK
        ("1.0.0-alpha.1", False),  # sem-ver converted to PEP-0440 "1.0.0a1"
        ("1.0.0-alpha", False),  # sem-ver converted to PEP-0440 "1.0.0a0"
        ("1.0.0-alpha.beta", True),  # sem-ver / LegacyVersion
        ("1.0.0-rc.1", False),  # sem-ver converted to PEP-0440 "1.0.0rc1"
        ("1.0.0-beta.11", False),  # sem-ver converted to PEP-0440 "1.0.0b11"
        ("1.0.0-beta.2", False),  # sem-ver converted to PEP-0440 "1.0.0b2"
        ("1.0.0-beta", False),  # sem-ver converted to PEP-0440 "1.0.0b0"
        ("1.0.0.2", False),  # PEP-0440 OK, sem-ver not
        ("1.0.0.0rc2", False),  # PEP-0440 OK, sem-ver not
        ("n.a.n", True),  # LegacyVersion (huh?)
        ("hot-fix-666", True),  # LegacyVersion (huh?)
        ("french toast", True),  # LegacyVersion (huh?)
    ],
)
def test_is_legacy_version(mocker, legacy_version, result):
    parser = mocker.spy(poetry.semver.version_utils.pep440_version, name="parse")
    assert is_legacy_version(legacy_version) == result
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


# TODO: sorted-pep440
# TODO: sorted-legacy
# TODO: sorted-packaging
# TODO: sorted-sem-ver
