from __future__ import annotations

import pytest

from packaging.utils import canonicalize_name
from poetry.core.packages.dependency_group import MAIN_GROUP
from poetry.core.version.markers import parse_marker

from poetry.packages.transitive_package_info import TransitivePackageInfo


DEV_GROUP = canonicalize_name("dev")


@pytest.mark.parametrize(
    "groups, expected",
    [
        (set(), "<empty>"),
        ({"main"}, 'sys_platform == "linux"'),
        ({"dev"}, 'python_version < "3.9"'),
        ({"main", "dev"}, 'sys_platform == "linux" or python_version < "3.9"'),
        ({"foo"}, "<empty>"),
        ({"main", "foo", "dev"}, 'sys_platform == "linux" or python_version < "3.9"'),
    ],
)
def test_get_marker(groups: set[str], expected: str) -> None:
    info = TransitivePackageInfo(
        depth=0,
        groups={MAIN_GROUP, DEV_GROUP},
        markers={
            MAIN_GROUP: parse_marker('sys_platform =="linux"'),
            DEV_GROUP: parse_marker('python_version < "3.9"'),
        },
    )
    assert str(info.get_marker([canonicalize_name(g) for g in groups])) == expected
