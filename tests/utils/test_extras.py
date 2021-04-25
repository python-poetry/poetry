import pytest

from poetry.core.packages.package import Package
from poetry.factory import Factory
from poetry.utils.extras import get_extra_package_names


_PACKAGE_FOO = Package("foo", "0.1.0")
_PACKAGE_SPAM = Package("spam", "0.2.0")
_PACKAGE_BAR = Package("bar", "0.3.0")
_PACKAGE_BAR.add_dependency(Factory.create_dependency("foo", "*"))

# recursive dependency
_PACKAGE_BAZ = Package("baz", "0.4.0")
_PACKAGE_BAZ.add_dependency(Factory.create_dependency("quix", "*"))
_PACKAGE_QUIX = Package("quix", "0.5.0")
_PACKAGE_QUIX.add_dependency(Factory.create_dependency("baz", "*"))


@pytest.mark.parametrize(
    "packages,extras,extra_names,expected_extra_package_names",
    [
        # Empty edge case
        ([], {}, [], []),
        # Selecting no extras is fine
        ([_PACKAGE_FOO], {}, [], []),
        # An empty extras group should return an empty list
        ([_PACKAGE_FOO], {"group0": []}, ["group0"], []),
        # Selecting an extras group should return the contained packages
        (
            [_PACKAGE_FOO, _PACKAGE_SPAM, _PACKAGE_BAR],
            {"group0": ["foo"]},
            ["group0"],
            ["foo"],
        ),
        # If a package has dependencies, we should also get their names
        (
            [_PACKAGE_FOO, _PACKAGE_SPAM, _PACKAGE_BAR],
            {"group0": ["bar"], "group1": ["spam"]},
            ["group0"],
            ["bar", "foo"],
        ),
        # Selecting multpile extras should get us the union of all package names
        (
            [_PACKAGE_FOO, _PACKAGE_SPAM, _PACKAGE_BAR],
            {"group0": ["bar"], "group1": ["spam"]},
            ["group0", "group1"],
            ["bar", "foo", "spam"],
        ),
        (
            [_PACKAGE_BAZ, _PACKAGE_QUIX],
            {"group0": ["baz"], "group1": ["quix"]},
            ["group0", "group1"],
            ["baz", "quix"],
        ),
    ],
)
def test_get_extra_package_names(
    packages, extras, extra_names, expected_extra_package_names
):
    assert expected_extra_package_names == list(
        get_extra_package_names(packages, extras, extra_names)
    )
