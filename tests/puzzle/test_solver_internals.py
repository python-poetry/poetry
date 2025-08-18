from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from packaging.utils import canonicalize_name
from poetry.core.constraints.version import parse_constraint
from poetry.core.packages.dependency import Dependency
from poetry.core.packages.dependency_group import MAIN_GROUP
from poetry.core.packages.package import Package
from poetry.core.version.markers import AnyMarker
from poetry.core.version.markers import parse_marker

from poetry.factory import Factory
from poetry.packages.transitive_package_info import TransitivePackageInfo
from poetry.puzzle.solver import PackageNode
from poetry.puzzle.solver import Solver
from poetry.puzzle.solver import depth_first_search
from poetry.puzzle.solver import merge_override_packages


if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Sequence

    from poetry.core.packages.project_package import ProjectPackage


DEV_GROUP = canonicalize_name("dev")


def dep(
    name: str,
    marker: str = "",
    extras: Iterable[str] = (),
    in_extras: Sequence[str] = (),
    groups: Iterable[str] = (),
) -> Dependency:
    d = Dependency(name, "1", groups=groups, extras=extras)
    d._in_extras = [canonicalize_name(e) for e in in_extras]
    if marker:
        d.marker = marker
    return d


def tm(info: TransitivePackageInfo) -> dict[str, str]:
    return {key: str(value) for key, value in info.markers.items()}


def test_dfs_depth(package: ProjectPackage) -> None:
    a = Package("a", "1")
    b = Package("b", "1")
    c = Package("c", "1")
    packages = [package, a, b, c]
    package.add_dependency(dep("a"))
    package.add_dependency(dep("b"))
    a.add_dependency(dep("b"))
    b.add_dependency(dep("c"))

    result, __ = depth_first_search(PackageNode(package, packages))
    depths = {
        nodes[0].package.complete_name: [node.depth for node in nodes]
        for nodes in result
    }

    assert depths == {"root": [-1], "a": [0], "b": [1], "c": [2]}


def test_dfs_depth_with_cycle(package: ProjectPackage) -> None:
    a = Package("a", "1")
    b = Package("b", "1")
    c = Package("c", "1")
    packages = [package, a, b, c]
    package.add_dependency(dep("a"))
    package.add_dependency(dep("b"))
    a.add_dependency(dep("b"))
    b.add_dependency(dep("a"))
    a.add_dependency(dep("c"))

    result, __ = depth_first_search(PackageNode(package, packages))
    depths = {
        nodes[0].package.complete_name: [node.depth for node in nodes]
        for nodes in result
    }

    assert depths == {"root": [-1], "a": [0], "b": [1], "c": [1]}


def test_dfs_depth_with_extra(package: ProjectPackage) -> None:
    a_foo = Package("a", "1", features=["foo"])
    a = Package("a", "1")
    b = Package("b", "1")
    c = Package("c", "1")
    packages = [package, a_foo, a, b, c]
    package.add_dependency(dep("a", extras=["foo"]))
    a_foo.add_dependency(dep("a"))
    a_foo.add_dependency(dep("b"))
    a_foo.add_dependency(dep("c", 'extra == "foo"'))
    a.add_dependency(dep("b"))

    result, __ = depth_first_search(PackageNode(package, packages))
    depths = {
        nodes[0].package.complete_name: [node.depth for node in nodes]
        for nodes in result
    }

    assert depths == {"root": [-1], "a[foo]": [0], "a": [0], "b": [1], "c": [1]}


def test_propagate_markers(package: ProjectPackage, solver: Solver) -> None:
    a = Package("a", "1")
    b = Package("b", "1")
    c = Package("c", "1")
    d = Package("d", "1")
    e = Package("e", "1")
    package.add_dependency(dep("a", 'sys_platform == "win32"'))
    package.add_dependency(dep("b", 'sys_platform == "linux"'))
    a.add_dependency(dep("c", 'python_version == "3.8"'))
    b.add_dependency(dep("d", 'python_version == "3.9"'))
    a.add_dependency(dep("e", 'python_version == "3.10"'))
    b.add_dependency(dep("e", 'python_version == "3.11"'))

    packages = [package, a, b, c, d, e]
    result = solver._aggregate_solved_packages(packages)

    assert len(result) == 6
    assert tm(result[package]) == {}
    assert tm(result[a]) == {"main": 'sys_platform == "win32"'}
    assert tm(result[b]) == {"main": 'sys_platform == "linux"'}
    assert tm(result[c]) == {
        "main": 'sys_platform == "win32" and python_version == "3.8"'
    }
    assert tm(result[d]) == {
        "main": 'sys_platform == "linux" and python_version == "3.9"'
    }
    assert tm(result[e]) == {
        "main": 'sys_platform == "win32" and python_version == "3.10"'
        ' or sys_platform == "linux" and python_version == "3.11"'
    }


def test_propagate_markers_same_name(package: ProjectPackage, solver: Solver) -> None:
    urls = {
        "linux": "https://files.pythonhosted.org/distributions/demo-0.1.0.tar.gz",
        "win32": (
            "https://files.pythonhosted.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
        ),
    }
    sdist = Package("demo", "0.1.0", source_type="url", source_url=urls["linux"])
    wheel = Package("demo", "0.1.0", source_type="url", source_url=urls["win32"])
    for platform, url in urls.items():
        package.add_dependency(
            Factory.create_dependency(
                "demo",
                {"url": url, "markers": f"sys_platform == '{platform}'"},
            )
        )

    packages = [package, sdist, wheel]
    result = solver._aggregate_solved_packages(packages)

    assert len(result) == 3
    assert tm(result[package]) == {}
    assert tm(result[sdist]) == {"main": 'sys_platform == "linux"'}
    assert tm(result[wheel]) == {"main": 'sys_platform == "win32"'}


def test_propagate_markers_with_extra(package: ProjectPackage, solver: Solver) -> None:
    a_foo = Package("a", "1", features=["foo"])
    a = Package("a", "1")
    b = Package("b", "1")
    c = Package("c", "1")
    d = Package("d", "1")
    package.add_dependency(dep("a", 'sys_platform == "win32"', extras=["foo"]))
    package.add_dependency(dep("b", 'sys_platform == "linux"'))
    a_foo.add_dependency(dep("a"))
    a_foo.add_dependency(dep("c", 'python_version == "3.8"'))
    a_foo.add_dependency(dep("d", 'extra == "foo"'))
    a.add_dependency(dep("c", 'python_version == "3.8"'))
    b.add_dependency(dep("a", 'python_version == "3.9"'))

    packages = [package, a_foo, a, b, c, d]
    result = solver._aggregate_solved_packages(packages)

    assert len(result) == len(packages) - 1
    assert tm(result[package]) == {}
    assert tm(result[a]) == {
        "main": (
            'sys_platform == "linux" and python_version == "3.9" or sys_platform == "win32"'
        )
    }
    assert tm(result[b]) == {"main": 'sys_platform == "linux"'}
    assert tm(result[c]) == {
        "main": 'sys_platform == "win32" and python_version == "3.8"'
    }
    assert tm(result[d]) == {"main": 'sys_platform == "win32"'}


def test_propagate_markers_with_root_extra(
    package: ProjectPackage, solver: Solver
) -> None:
    a = Package("a", "1")
    b = Package("b", "1")
    c = Package("c", "1")
    d = Package("d", "1")
    # "extra" is not present in the marker of an extra dependency of the root package,
    # there is only "in_extras"...
    package.add_dependency(dep("a", in_extras=["foo"]))
    package.add_dependency(
        dep("b", 'sys_platform == "linux"', in_extras=["foo", "bar"])
    )
    a.add_dependency(dep("c", 'python_version == "3.8"'))
    b.add_dependency(dep("d", 'python_version == "3.9"'))

    packages = [package, a, b, c, d]
    result = solver._aggregate_solved_packages(packages)

    assert len(result) == len(packages)
    assert tm(result[package]) == {}
    assert tm(result[a]) == {"main": 'extra == "foo"'}
    assert tm(result[b]) == {
        "main": 'sys_platform == "linux" and (extra == "foo" or extra == "bar")',
    }
    assert tm(result[c]) == {"main": 'extra == "foo" and python_version == "3.8"'}
    assert tm(result[d]) == {
        "main": (
            'sys_platform == "linux" and (extra == "foo" or extra == "bar")'
            ' and python_version == "3.9"'
        )
    }


def test_propagate_markers_with_duplicate_dependency_root_extra(
    package: ProjectPackage, solver: Solver
) -> None:
    a = Package("a", "1")
    package.add_dependency(dep("a"))
    # "extra" is not present in the marker of an extra dependency of the root package,
    # there is only "in_extras"...
    package.add_dependency(dep("a", in_extras=["foo"]))

    packages = [package, a]
    result = solver._aggregate_solved_packages(packages)

    assert len(result) == len(packages)
    assert tm(result[package]) == {}
    assert tm(result[a]) == {"main": ""}  # not "extra == 'foo'" !


def test_propagate_groups_with_extra(package: ProjectPackage, solver: Solver) -> None:
    a_foo = Package("a", "1", features=["foo"])
    a = Package("a", "1")
    b = Package("b", "1")
    c = Package("c", "1")
    package.add_dependency(dep("a", groups=["main"]))
    package.add_dependency(dep("a", groups=["dev"], extras=["foo"]))
    a_foo.add_dependency(dep("a"))
    a_foo.add_dependency(dep("b"))
    a_foo.add_dependency(dep("c", 'extra == "foo"'))
    a.add_dependency(dep("b"))

    packages = [package, a_foo, a, b, c]
    result = solver._aggregate_solved_packages(packages)

    assert len(result) == len(packages) - 1
    assert result[package].groups == set()
    assert result[a].groups == {"main", "dev"}
    assert result[b].groups == {"main", "dev"}
    assert result[c].groups == {"dev"}


def test_propagate_markers_for_groups1(package: ProjectPackage, solver: Solver) -> None:
    a = Package("a", "1")
    b = Package("b", "1")
    c = Package("c", "1")
    package.add_dependency(dep("a", 'sys_platform == "win32"', groups=["main"]))
    package.add_dependency(dep("b", 'sys_platform == "linux"', groups=["dev"]))
    a.add_dependency(dep("c", 'python_version == "3.8"'))
    b.add_dependency(dep("c", 'python_version == "3.9"'))

    packages = [package, a, b, c]
    result = solver._aggregate_solved_packages(packages)

    assert len(result) == len(packages)
    assert result[package].groups == set()
    assert result[a].groups == {"main"}
    assert result[b].groups == {"dev"}
    assert result[c].groups == {"main", "dev"}
    assert tm(result[package]) == {}
    assert tm(result[a]) == {"main": 'sys_platform == "win32"'}
    assert tm(result[b]) == {"dev": 'sys_platform == "linux"'}
    assert tm(result[c]) == {
        "main": 'sys_platform == "win32" and python_version == "3.8"',
        "dev": 'sys_platform == "linux" and python_version == "3.9"',
    }


def test_propagate_markers_for_groups2(package: ProjectPackage, solver: Solver) -> None:
    a = Package("a", "1")
    b = Package("b", "1")
    c = Package("c", "1")
    d = Package("d", "1")
    package.add_dependency(dep("a", 'sys_platform == "win32"', groups=["main"]))
    package.add_dependency(dep("b", 'sys_platform == "linux"', groups=["dev"]))
    package.add_dependency(dep("c", 'sys_platform == "darwin"', groups=["main", "dev"]))
    a.add_dependency(dep("d", 'python_version == "3.8"'))
    b.add_dependency(dep("d", 'python_version == "3.9"'))
    c.add_dependency(dep("d", 'python_version == "3.10"'))

    packages = [package, a, b, c, d]
    result = solver._aggregate_solved_packages(packages)

    assert len(result) == len(packages)
    assert result[package].groups == set()
    assert result[a].groups == {"main"}
    assert result[b].groups == {"dev"}
    assert result[c].groups == {"main", "dev"}
    assert result[d].groups == {"main", "dev"}
    assert tm(result[package]) == {}
    assert tm(result[a]) == {"main": 'sys_platform == "win32"'}
    assert tm(result[b]) == {"dev": 'sys_platform == "linux"'}
    assert tm(result[c]) == {
        "main": 'sys_platform == "darwin"',
        "dev": 'sys_platform == "darwin"',
    }
    assert tm(result[d]) == {
        "main": (
            'sys_platform == "win32" and python_version == "3.8"'
            ' or sys_platform == "darwin" and python_version == "3.10"'
        ),
        "dev": (
            'sys_platform == "darwin" and python_version == "3.10"'
            ' or sys_platform == "linux" and python_version == "3.9"'
        ),
    }


def test_propagate_markers_with_cycle(package: ProjectPackage, solver: Solver) -> None:
    a = Package("a", "1")
    b = Package("b", "1")
    package.add_dependency(dep("a", 'sys_platform == "win32"'))
    package.add_dependency(dep("b", 'sys_platform == "linux"'))
    a.add_dependency(dep("b", 'python_version == "3.8"'))
    b.add_dependency(dep("a", 'python_version == "3.9"'))

    packages = [package, a, b]
    result = solver._aggregate_solved_packages(packages)

    assert len(result) == 3
    assert tm(result[package]) == {}
    assert tm(result[a]) == {
        "main": (
            'sys_platform == "linux" and python_version == "3.9"'
            ' or sys_platform == "win32"'
        )
    }
    assert tm(result[b]) == {
        "main": (
            'sys_platform == "win32" and python_version == "3.8"'
            ' or sys_platform == "linux"'
        )
    }


def test_merge_override_packages_restricted(package: ProjectPackage) -> None:
    """Markers of dependencies should be intersected with override markers."""
    a = Package("a", "1")

    packages = merge_override_packages(
        [
            (
                {package: {"a": dep("b", 'python_version < "3.9"')}},
                {
                    a: TransitivePackageInfo(
                        0,
                        {MAIN_GROUP},
                        {MAIN_GROUP: parse_marker("sys_platform == 'win32'")},
                    )
                },
            ),
            (
                {package: {"a": dep("b", 'python_version >= "3.9"')}},
                {
                    a: TransitivePackageInfo(
                        0,
                        {MAIN_GROUP},
                        {MAIN_GROUP: parse_marker("sys_platform == 'linux'")},
                    )
                },
            ),
        ],
        parse_constraint("*"),
    )
    assert len(packages) == 1
    assert packages[a].groups == {"main"}
    assert tm(packages[a]) == {
        "main": (
            'python_version < "3.9" and sys_platform == "win32"'
            ' or sys_platform == "linux" and python_version >= "3.9"'
        )
    }


def test_merge_override_packages_extras(package: ProjectPackage) -> None:
    """Extras from overrides should not be visible in the resulting marker."""
    a = Package("a", "1")

    packages = merge_override_packages(
        [
            (
                {package: {"a": dep("b", 'python_version < "3.9" and extra == "foo"')}},
                {
                    a: TransitivePackageInfo(
                        0,
                        {MAIN_GROUP},
                        {MAIN_GROUP: parse_marker("sys_platform == 'win32'")},
                    )
                },
            ),
            (
                {
                    package: {
                        "a": dep("b", 'python_version >= "3.9" and extra == "foo"')
                    }
                },
                {
                    a: TransitivePackageInfo(
                        0,
                        {MAIN_GROUP},
                        {MAIN_GROUP: parse_marker("sys_platform == 'linux'")},
                    )
                },
            ),
        ],
        parse_constraint("*"),
    )
    assert len(packages) == 1
    assert packages[a].groups == {"main"}
    assert tm(packages[a]) == {
        "main": (
            'python_version < "3.9" and sys_platform == "win32"'
            ' or sys_platform == "linux" and python_version >= "3.9"'
        )
    }


@pytest.mark.parametrize(
    ("python_constraint", "expected"),
    [
        (">=3.8", 'python_version > "3.8" or sys_platform != "linux"'),
        (">=3.9", ""),
    ],
)
def test_merge_override_packages_python_constraint(
    package: ProjectPackage, python_constraint: str, expected: str
) -> None:
    """The resulting marker depends on the project's python constraint."""
    a = Package("a", "1")

    packages = merge_override_packages(
        [
            (
                {
                    package: {
                        "a": dep(
                            "b", "sys_platform == 'linux' and python_version > '3.8'"
                        )
                    }
                },
                {a: TransitivePackageInfo(0, {MAIN_GROUP}, {MAIN_GROUP: AnyMarker()})},
            ),
            (
                {package: {"a": dep("b", "sys_platform != 'linux'")}},
                {a: TransitivePackageInfo(0, {MAIN_GROUP}, {MAIN_GROUP: AnyMarker()})},
            ),
        ],
        parse_constraint(python_constraint),
    )
    assert len(packages) == 1
    assert packages[a].groups == {"main"}
    assert tm(packages[a]) == {"main": expected}


def test_merge_override_packages_multiple_deps(package: ProjectPackage) -> None:
    """All override markers should be intersected."""
    a = Package("a", "1")

    packages = merge_override_packages(
        [
            (
                {
                    package: {
                        "a": dep("b", 'python_version < "3.9"'),
                        "c": dep("d", 'sys_platform == "linux"'),
                    },
                    a: {"e": dep("f", 'python_version >= "3.8"')},
                },
                {a: TransitivePackageInfo(0, {MAIN_GROUP}, {MAIN_GROUP: AnyMarker()})},
            ),
        ],
        parse_constraint("*"),
    )

    assert len(packages) == 1
    assert packages[a].groups == {"main"}
    assert tm(packages[a]) == {
        "main": 'python_version == "3.8" and sys_platform == "linux"'
    }


def test_merge_override_packages_groups(package: ProjectPackage) -> None:
    a = Package("a", "1")
    b = Package("b", "1")

    packages = merge_override_packages(
        [
            (
                {package: {"a": dep("b", 'python_version < "3.9"')}},
                {
                    a: TransitivePackageInfo(
                        0,
                        {MAIN_GROUP},
                        {MAIN_GROUP: parse_marker("sys_platform == 'win32'")},
                    ),
                    b: TransitivePackageInfo(
                        0,
                        {MAIN_GROUP, DEV_GROUP},
                        {
                            MAIN_GROUP: parse_marker("sys_platform == 'win32'"),
                            DEV_GROUP: parse_marker("sys_platform == 'linux'"),
                        },
                    ),
                },
            ),
            (
                {package: {"a": dep("b", 'python_version >= "3.9"')}},
                {
                    a: TransitivePackageInfo(
                        0,
                        {DEV_GROUP},
                        {DEV_GROUP: parse_marker("sys_platform == 'linux'")},
                    ),
                    b: TransitivePackageInfo(
                        0,
                        {MAIN_GROUP, DEV_GROUP},
                        {
                            MAIN_GROUP: parse_marker("platform_machine == 'amd64'"),
                            DEV_GROUP: parse_marker("platform_machine == 'aarch64'"),
                        },
                    ),
                },
            ),
        ],
        parse_constraint("*"),
    )
    assert len(packages) == 2
    assert packages[a].groups == {"main", "dev"}
    assert tm(packages[a]) == {
        "main": 'python_version < "3.9" and sys_platform == "win32"',
        "dev": 'python_version >= "3.9" and sys_platform == "linux"',
    }
    assert packages[b].groups == {"main", "dev"}
    assert tm(packages[b]) == {
        "main": (
            'python_version < "3.9" and sys_platform == "win32"'
            ' or python_version >= "3.9" and platform_machine == "amd64"'
        ),
        "dev": (
            'python_version < "3.9" and sys_platform == "linux"'
            ' or python_version >= "3.9" and platform_machine == "aarch64"'
        ),
    }


def test_merge_override_packages_shortcut(package: ProjectPackage) -> None:
    a = Package("a", "1")
    common_marker = (
        'extra == "test" and sys_platform == "win32" or platform_system == "Windows"'
        ' or sys_platform == "linux" and extra == "stretch"'
    )
    override_marker1 = 'python_version >= "3.12" and platform_system != "Emscripten"'
    override_marker2 = 'python_version >= "3.12" and platform_system == "Emscripten"'

    packages = merge_override_packages(
        [
            (
                {package: {"a": dep("b", override_marker1)}},
                {
                    a: TransitivePackageInfo(
                        0,
                        {MAIN_GROUP},
                        {
                            MAIN_GROUP: parse_marker(
                                f"{override_marker1} and ({common_marker})"
                            )
                        },
                    )
                },
            ),
            (
                {package: {"a": dep("b", override_marker2)}},
                {
                    a: TransitivePackageInfo(
                        0,
                        {MAIN_GROUP},
                        {
                            MAIN_GROUP: parse_marker(
                                f"{override_marker2} and ({common_marker})"
                            )
                        },
                    )
                },
            ),
        ],
        parse_constraint("*"),
    )
    assert len(packages) == 1
    assert packages[a].groups == {"main"}
    assert tm(packages[a]) == {
        "main": f'({common_marker}) and python_version >= "3.12"'
    }


# TODO: root extras
