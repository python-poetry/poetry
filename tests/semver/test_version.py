import pytest

from poetry.semver import EmptyConstraint
from poetry.semver import Version
from poetry.semver import VersionRange
from poetry.semver.exceptions import ParseVersionError


@pytest.mark.parametrize(
    "input,version",
    [
        ("1.0.0", Version(1, 0, 0)),
        ("1", Version(1, 0, 0)),
        ("1.0", Version(1, 0, 0)),
        ("1b1", Version(1, 0, 0, pre="beta1")),
        ("1.0b1", Version(1, 0, 0, pre="beta1")),
        ("1.0.0b1", Version(1, 0, 0, pre="beta1")),
        ("1.0.0-b1", Version(1, 0, 0, pre="beta1")),
        ("1.0.0-beta.1", Version(1, 0, 0, pre="beta1")),
        ("1.0.0+1", Version(1, 0, 0, build="1")),
        ("1.0.0-1", Version(1, 0, 0, build="1")),
        ("1.0.0.0", Version(1, 0, 0)),
        ("1.0.0-post", Version(1, 0, 0)),
        ("1.0.0-post1", Version(1, 0, 0, build="1")),
        ("0.6c", Version(0, 6, 0, pre="rc0")),
        ("0.6pre", Version(0, 6, 0, pre="rc0")),
    ],
)
def test_parse_valid(input, version):
    parsed = Version.parse(input)

    assert parsed == version
    assert parsed.text == input


@pytest.mark.parametrize("input", [(None, "example")])
def test_parse_invalid(input):
    with pytest.raises(ParseVersionError):
        Version.parse(input)


def test_comparison():
    versions = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0-rc.1+build.1",
        "1.0.0",
        "1.0.0+0.3.7",
        "1.3.7+build",
        "1.3.7+build.2.b8f12d7",
        "1.3.7+build.11.e0f985a",
        "2.0.0",
        "2.1.0",
        "2.2.0",
        "2.11.0",
        "2.11.1",
    ]

    for i in range(len(versions)):
        for j in range(len(versions)):
            a = Version.parse(versions[i])
            b = Version.parse(versions[j])

            assert (a < b) == (i < j)
            assert (a > b) == (i > j)
            assert (a <= b) == (i <= j)
            assert (a >= b) == (i >= j)
            assert (a == b) == (i == j)
            assert (a != b) == (i != j)


def test_equality():
    assert Version.parse("1.2.3") == Version.parse("01.2.3")
    assert Version.parse("1.2.3") == Version.parse("1.02.3")
    assert Version.parse("1.2.3") == Version.parse("1.2.03")
    assert Version.parse("1.2.3-1") == Version.parse("1.2.3-01")
    assert Version.parse("1.2.3+1") == Version.parse("1.2.3+01")


def test_allows():
    v = Version.parse("1.2.3")
    assert v.allows(v)
    assert not v.allows(Version.parse("2.2.3"))
    assert not v.allows(Version.parse("1.3.3"))
    assert not v.allows(Version.parse("1.2.4"))
    assert not v.allows(Version.parse("1.2.3-dev"))
    assert not v.allows(Version.parse("1.2.3+build"))


def test_allows_all():
    v = Version.parse("1.2.3")

    assert v.allows_all(v)
    assert not v.allows_all(Version.parse("0.0.3"))
    assert not v.allows_all(
        VersionRange(Version.parse("1.1.4"), Version.parse("1.2.4"))
    )
    assert not v.allows_all(VersionRange())
    assert v.allows_all(EmptyConstraint())


def test_allows_any():
    v = Version.parse("1.2.3")

    assert v.allows_any(v)
    assert not v.allows_any(Version.parse("0.0.3"))
    assert v.allows_any(VersionRange(Version.parse("1.1.4"), Version.parse("1.2.4")))
    assert v.allows_any(VersionRange())
    assert not v.allows_any(EmptyConstraint())


def test_intersect():
    v = Version.parse("1.2.3")

    assert v.intersect(v) == v
    assert v.intersect(Version.parse("1.1.4")).is_empty()
    assert (
        v.intersect(VersionRange(Version.parse("1.1.4"), Version.parse("1.2.4"))) == v
    )
    assert (
        Version.parse("1.1.4")
        .intersect(VersionRange(v, Version.parse("1.2.4")))
        .is_empty()
    )


def test_union():
    v = Version.parse("1.2.3")

    assert v.union(v) == v

    result = v.union(Version.parse("0.8.0"))
    assert result.allows(v)
    assert result.allows(Version.parse("0.8.0"))
    assert not result.allows(Version.parse("1.1.4"))

    range = VersionRange(Version.parse("1.1.4"), Version.parse("1.2.4"))
    assert v.union(range) == range

    union = Version.parse("1.1.4").union(
        VersionRange(Version.parse("1.1.4"), Version.parse("1.2.4"))
    )
    assert union == VersionRange(
        Version.parse("1.1.4"), Version.parse("1.2.4"), include_min=True
    )

    result = v.union(VersionRange(Version.parse("0.0.3"), Version.parse("1.1.4")))
    assert result.allows(v)
    assert result.allows(Version.parse("0.1.0"))


def test_difference():
    v = Version.parse("1.2.3")

    assert v.difference(v).is_empty()
    assert v.difference(Version.parse("0.8.0")) == v
    assert v.difference(
        VersionRange(Version.parse("1.1.4"), Version.parse("1.2.4"))
    ).is_empty()
    assert (
        v.difference(VersionRange(Version.parse("1.4.0"), Version.parse("3.0.0"))) == v
    )
