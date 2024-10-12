from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING
from unittest.mock import PropertyMock

import pytest

from packaging.utils import canonicalize_name
from poetry.core.constraints.version import Version
from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link

from poetry.repositories.link_sources.base import LinkSource


if TYPE_CHECKING:
    from collections.abc import Iterable

    from pytest_mock import MockerFixture


@pytest.fixture
def link_source(mocker: MockerFixture) -> LinkSource:
    url = "https://example.org"
    link_source = LinkSource(url)
    mocker.patch(
        f"{LinkSource.__module__}.{LinkSource.__qualname__}._link_cache",
        new_callable=PropertyMock,
        return_value=defaultdict(
            lambda: defaultdict(list),
            {
                canonicalize_name("demo"): defaultdict(
                    list,
                    {
                        Version.parse("0.1.0"): [
                            Link(f"{url}/demo-0.1.0.tar.gz"),
                            Link(f"{url}/demo-0.1.0-py2.py3-none-any.whl"),
                        ],
                        Version.parse("0.1.1"): [Link(f"{url}/demo-0.1.1.tar.gz")],
                    },
                ),
            },
        ),
    )
    return link_source


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("demo-0.1.0-py2.py3-none-any.whl", Package("demo", "0.1.0")),
        ("demo-0.1.0.tar.gz", Package("demo", "0.1.0")),
        ("demo-0.1.0.egg", Package("demo", "0.1.0")),
        ("demo-0.1.0_invalid-py2.py3-none-any.whl", None),  # invalid version
        ("demo-0.1.0_invalid.egg", None),  # invalid version
        ("no-package-at-all.txt", None),
    ],
)
def test_link_package_data(filename: str, expected: Package | None) -> None:
    link = Link(f"https://example.org/{filename}")
    assert LinkSource.link_package_data(link) == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("demo", {Version.parse("0.1.0"), Version.parse("0.1.1")}),
        ("invalid", set()),
    ],
)
def test_versions(name: str, expected: set[Version], link_source: LinkSource) -> None:
    assert set(link_source.versions(canonicalize_name(name))) == expected


def test_packages(link_source: LinkSource) -> None:
    expected = {
        Package("demo", "0.1.0"),
        Package("demo", "0.1.0"),
        Package("demo", "0.1.1"),
    }
    assert set(link_source.packages) == expected


@pytest.mark.parametrize(
    "version_string, filenames",
    [
        ("0.1.0", ["demo-0.1.0.tar.gz", "demo-0.1.0-py2.py3-none-any.whl"]),
        ("0.1.1", ["demo-0.1.1.tar.gz"]),
        ("0.1.2", []),
    ],
)
def test_links_for_version(
    version_string: str, filenames: Iterable[str], link_source: LinkSource
) -> None:
    version = Version.parse(version_string)
    expected = {Link(f"{link_source.url}/{name}") for name in filenames}
    assert (
        set(link_source.links_for_version(canonicalize_name("demo"), version))
        == expected
    )
