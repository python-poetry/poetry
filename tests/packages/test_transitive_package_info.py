from __future__ import annotations

import pytest

from poetry.core.version.markers import parse_marker

from poetry.packages.transitive_package_info import TransitivePackageInfo


@pytest.mark.parametrize(
    "groups, expected",
    [
        ([], "<empty>"),
        (["main"], 'sys_platform == "linux"'),
        (["dev"], 'python_version < "3.9"'),
        (["main", "dev"], 'sys_platform == "linux" or python_version < "3.9"'),
        (["foo"], "<empty>"),
        (["main", "foo", "dev"], 'sys_platform == "linux" or python_version < "3.9"'),
    ],
)
def test_get_marker(groups: list[str], expected: str) -> None:
    info = TransitivePackageInfo(
        depth=0,
        groups={"main", "dev"},
        markers={
            "main": parse_marker('sys_platform =="linux"'),
            "dev": parse_marker('python_version < "3.9"'),
        },
    )
    assert str(info.get_marker(groups)) == expected
