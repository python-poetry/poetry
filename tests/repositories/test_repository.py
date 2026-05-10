from __future__ import annotations

import pytest

from poetry.core.constraints.version import Version

from poetry.factory import Factory
from poetry.repositories import Repository
from tests.helpers import get_package


@pytest.fixture(scope="module")
def repository() -> Repository:
    repo = Repository("repo")

    # latest version pre-release
    repo.add_package(get_package("foo", "1.0"))
    repo.add_package(get_package("foo", "2.0b0"))

    # latest version yanked
    repo.add_package(get_package("black", "19.10b0"))
    repo.add_package(get_package("black", "21.11b0", yanked="reason"))

    return repo


@pytest.mark.parametrize(
    ("allow_prereleases", "constraint", "expected"),
    [
        (None, ">=1.0", ["1.0"]),
        (False, ">=1.0", ["1.0"]),
        (True, ">=1.0", ["1.0", "2.0b0"]),
        (None, ">=1.5", ["2.0b0"]),
        (False, ">=1.5", []),
        (True, ">=1.5", ["2.0b0"]),
    ],
)
def test_find_packages_allow_prereleases(
    repository: Repository,
    allow_prereleases: bool | None,
    constraint: str,
    expected: list[str],
) -> None:
    packages = repository.find_packages(
        Factory.create_dependency(
            "foo", {"version": constraint, "allow-prereleases": allow_prereleases}
        )
    )

    assert [str(p.version) for p in packages] == expected


@pytest.mark.parametrize(
    ["constraint", "expected"],
    [
        # yanked 21.11b0 is ignored except for pinned version
        ("*", ["19.10b0"]),
        (">=19.0a0", ["19.10b0"]),
        (">=20.0a0", []),
        (">=21.11b0", []),
        ("==21.11b0", ["21.11b0"]),
    ],
)
def test_find_packages_yanked(
    repository: Repository, constraint: str, expected: list[str]
) -> None:
    packages = repository.find_packages(Factory.create_dependency("black", constraint))

    assert [str(p.version) for p in packages] == expected


@pytest.mark.parametrize(
    "package_name, version, yanked, yanked_reason",
    [
        ("black", "19.10b0", False, ""),
        ("black", "21.11b0", True, "reason"),
    ],
)
def test_package_yanked(
    repository: Repository,
    package_name: str,
    version: str,
    yanked: bool,
    yanked_reason: str,
) -> None:
    package = repository.package(package_name, Version.parse(version))

    assert package.name == package_name
    assert str(package.version) == version
    assert package.yanked is yanked
    assert package.yanked_reason == yanked_reason


def test_package_pretty_name_is_kept() -> None:
    pretty_name = "Not_canoni-calized.name"
    repo = Repository("repo")
    repo.add_package(get_package(pretty_name, "1.0"))
    package = repo.package(pretty_name, Version.parse("1.0"))

    assert package.pretty_name == pretty_name


def test_search() -> None:
    package_foo1 = get_package("foo", "1.0.0")
    package_foo2 = get_package("foo", "2.0.0")
    package_foobar = get_package("foobar", "1.0.0")
    repo = Repository("repo", [package_foo1, package_foo2, package_foobar])

    assert repo.search("foo") == [package_foo1, package_foo2, package_foobar]
    assert repo.search("bar") == [package_foobar]
    assert repo.search("nothing") == []
