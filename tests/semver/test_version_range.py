import pytest

from poetry.semver import EmptyConstraint
from poetry.semver import Version
from poetry.semver import VersionRange


@pytest.fixture()
def v003():
    return Version.parse("0.0.3")


@pytest.fixture()
def v010():
    return Version.parse("0.1.0")


@pytest.fixture()
def v080():
    return Version.parse("0.8.0")


@pytest.fixture()
def v072():
    return Version.parse("0.7.2")


@pytest.fixture()
def v114():
    return Version.parse("1.1.4")


@pytest.fixture()
def v123():
    return Version.parse("1.2.3")


@pytest.fixture()
def v124():
    return Version.parse("1.2.4")


@pytest.fixture()
def v130():
    return Version.parse("1.3.0")


@pytest.fixture()
def v140():
    return Version.parse("1.4.0")


@pytest.fixture()
def v200():
    return Version.parse("2.0.0")


@pytest.fixture()
def v234():
    return Version.parse("2.3.4")


@pytest.fixture()
def v250():
    return Version.parse("2.5.0")


@pytest.fixture()
def v300():
    return Version.parse("3.0.0")


def test_allows_all(v003, v010, v080, v114, v123, v124, v140, v200, v234, v250, v300):
    assert VersionRange(v123, v250).allows_all(EmptyConstraint())

    range = VersionRange(v123, v250, include_max=True)
    assert not range.allows_all(v123)
    assert range.allows_all(v124)
    assert range.allows_all(v250)
    assert not range.allows_all(v300)

    # with no min
    range = VersionRange(max=v250)
    assert range.allows_all(VersionRange(v080, v140))
    assert not range.allows_all(VersionRange(v080, v300))
    assert range.allows_all(VersionRange(max=v140))
    assert not range.allows_all(VersionRange(max=v300))
    assert range.allows_all(range)
    assert not range.allows_all(VersionRange())

    # with no max
    range = VersionRange(min=v010)
    assert range.allows_all(VersionRange(v080, v140))
    assert not range.allows_all(VersionRange(v003, v140))
    assert range.allows_all(VersionRange(v080))
    assert not range.allows_all(VersionRange(v003))
    assert range.allows_all(range)
    assert not range.allows_all(VersionRange())

    # Allows bordering range that is not more inclusive
    exclusive = VersionRange(v010, v250)
    inclusive = VersionRange(v010, v250, True, True)
    assert inclusive.allows_all(exclusive)
    assert inclusive.allows_all(inclusive)
    assert not exclusive.allows_all(inclusive)
    assert exclusive.allows_all(exclusive)

    # Allows unions that are completely contained
    range = VersionRange(v114, v200)
    assert range.allows_all(VersionRange(v123, v124).union(v140))
    assert not range.allows_all(VersionRange(v010, v124).union(v140))
    assert not range.allows_all(VersionRange(v123, v234).union(v140))


def test_allows_any(
    v003, v010, v072, v080, v114, v123, v124, v140, v200, v234, v250, v300
):
    # disallows an empty constraint
    assert not VersionRange(v123, v250).allows_any(EmptyConstraint())

    # allows allowed versions
    range = VersionRange(v123, v250, include_max=True)
    assert not range.allows_any(v123)
    assert range.allows_any(v124)
    assert range.allows_any(v250)
    assert not range.allows_any(v300)

    # with no min
    range = VersionRange(max=v200)
    assert range.allows_any(VersionRange(v140, v300))
    assert not range.allows_any(VersionRange(v234, v300))
    assert range.allows_any(VersionRange(v140))
    assert not range.allows_any(VersionRange(v234))
    assert range.allows_any(range)

    # with no max
    range = VersionRange(min=v072)
    assert range.allows_any(VersionRange(v003, v140))
    assert not range.allows_any(VersionRange(v003, v010))
    assert range.allows_any(VersionRange(max=v080))
    assert not range.allows_any(VersionRange(max=v003))
    assert range.allows_any(range)

    # with min and max
    range = VersionRange(v072, v200)
    assert range.allows_any(VersionRange(v003, v140))
    assert range.allows_any(VersionRange(v140, v300))
    assert not range.allows_any(VersionRange(v003, v010))
    assert not range.allows_any(VersionRange(v234, v300))
    assert not range.allows_any(VersionRange(max=v010))
    assert not range.allows_any(VersionRange(v234))
    assert range.allows_any(range)

    # allows a bordering range when both are inclusive
    assert not VersionRange(max=v250).allows_any(VersionRange(min=v250))
    assert not VersionRange(max=v250, include_max=True).allows_any(
        VersionRange(min=v250)
    )
    assert not VersionRange(max=v250).allows_any(
        VersionRange(min=v250, include_min=True)
    )
    assert not VersionRange(min=v250).allows_any(VersionRange(max=v250))
    assert VersionRange(max=v250, include_max=True).allows_any(
        VersionRange(min=v250, include_min=True)
    )

    # allows unions that are partially contained'
    range = VersionRange(v114, v200)
    assert range.allows_any(VersionRange(v010, v080).union(v140))
    assert range.allows_any(VersionRange(v123, v234).union(v300))
    assert not range.allows_any(VersionRange(v234, v300).union(v010))

    # pre-release min does not allow lesser than itself
    range = VersionRange(Version.parse("1.9b1"), include_min=True)
    assert not range.allows_any(
        VersionRange(
            Version.parse("1.8.0"),
            Version.parse("1.9.0"),
            include_min=True,
            always_include_max_prerelease=True,
        )
    )


def test_intersect(v114, v123, v124, v200, v250, v300):
    # two overlapping ranges
    assert VersionRange(v123, v250).intersect(VersionRange(v200, v300)) == VersionRange(
        v200, v250
    )

    # a non-overlapping range allows no versions
    a = VersionRange(v114, v124)
    b = VersionRange(v200, v250)
    assert a.intersect(b).is_empty()

    # adjacent ranges allow no versions if exclusive
    a = VersionRange(v114, v124)
    b = VersionRange(v124, v200)
    assert a.intersect(b).is_empty()

    # adjacent ranges allow version if inclusive
    a = VersionRange(v114, v124, include_max=True)
    b = VersionRange(v124, v200, include_min=True)
    assert a.intersect(b) == v124

    # with an open range
    open = VersionRange()
    a = VersionRange(v114, v124)
    assert open.intersect(open) == open
    assert open.intersect(a) == a

    # returns the version if the range allows it
    assert VersionRange(v114, v124).intersect(v123) == v123
    assert VersionRange(v123, v124).intersect(v114).is_empty()


def test_union(
    v003, v010, v072, v080, v114, v123, v124, v130, v140, v200, v234, v250, v300
):
    # with a version returns the range if it contains the version
    range = VersionRange(v114, v124)
    assert range.union(v123) == range

    # with a version on the edge of the range, expands the range
    range = VersionRange(v114, v124)
    assert range.union(v124) == VersionRange(v114, v124, include_max=True)
    assert range.union(v114) == VersionRange(v114, v124, include_min=True)

    # with a version allows both the range and the version if the range
    # doesn't contain the version
    result = VersionRange(v003, v114).union(v124)
    assert result.allows(v010)
    assert not result.allows(v123)
    assert result.allows(v124)

    # returns a VersionUnion for a disjoint range
    result = VersionRange(v003, v114).union(VersionRange(v130, v200))
    assert result.allows(v080)
    assert not result.allows(v123)
    assert result.allows(v140)

    # considers open ranges disjoint
    result = VersionRange(v003, v114).union(VersionRange(v114, v200))
    assert result.allows(v080)
    assert not result.allows(v114)
    assert result.allows(v140)
    result = VersionRange(v114, v200).union(VersionRange(v003, v114))
    assert result.allows(v080)
    assert not result.allows(v114)
    assert result.allows(v140)

    # returns a merged range for an overlapping range
    result = VersionRange(v003, v114).union(VersionRange(v080, v200))
    assert result == VersionRange(v003, v200)

    # considers closed ranges overlapping
    result = VersionRange(v003, v114, include_max=True).union(VersionRange(v114, v200))
    assert result == VersionRange(v003, v200)
    result = VersionRange(v003, v114).union(VersionRange(v114, v200, include_min=True))
    assert result == VersionRange(v003, v200)
