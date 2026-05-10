from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.core.version.markers import parse_marker

from poetry.factory import Factory
from tests.helpers import get_package


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from tests.helpers import DummyRepository
    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("debug resolve")


@pytest.fixture(autouse=True)
def __add_packages(repo: DummyRepository) -> None:
    cachy020 = get_package("cachy", "0.2.0")
    cachy020.add_dependency(Factory.create_dependency("msgpack-python", ">=0.5 <0.6"))

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy020)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    repo.add_package(get_package("pendulum", "2.0.3"))
    repo.add_package(get_package("cleo", "0.6.5"))


def test_debug_resolve_gives_resolution_results(tester: CommandTester) -> None:
    tester.execute("cachy")

    expected = """\
Resolving dependencies...

Resolution results:

msgpack-python 0.5.3
cachy          0.2.0
"""

    assert tester.io.fetch_output() == expected


def test_debug_resolve_tree_option_gives_the_dependency_tree(
    tester: CommandTester,
) -> None:
    tester.execute("cachy --tree")

    expected = """\
Resolving dependencies...

Resolution results:

cachy 0.2.0
└── msgpack-python >=0.5 <0.6
"""

    assert tester.io.fetch_output() == expected


def test_debug_resolve_shows_marker_when_present(
    tester: CommandTester, repo: DummyRepository
) -> None:
    """Packages with environment markers must show the marker in output."""
    pkg = get_package("pathlib2", "2.3.0")
    pkg.marker = parse_marker('sys_platform == "win32"')
    repo.add_package(pkg)

    tester.execute("pathlib2")

    expected = """\
Resolving dependencies...

Resolution results:

pathlib2 2.3.0 sys_platform == "win32"
"""

    assert tester.io.fetch_output() == expected


def test_debug_resolve_git_dependency(tester: CommandTester) -> None:
    tester.execute("git+https://github.com/demo/demo.git")

    expected = """\
Resolving dependencies...

Resolution results:

pendulum 2.0.3
demo     0.1.2
"""

    assert tester.io.fetch_output() == expected
