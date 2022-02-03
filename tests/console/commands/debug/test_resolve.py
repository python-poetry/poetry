from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.factory import Factory
from tests.helpers import get_package


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("debug resolve")


@pytest.fixture(autouse=True)
def __add_packages(repo: TestRepository) -> None:
    cachy020 = get_package("cachy", "0.2.0")
    cachy020.add_dependency(Factory.create_dependency("msgpack-python", ">=0.5 <0.6"))

    repo.add_package(get_package("cachy", "0.1.0"))
    repo.add_package(cachy020)
    repo.add_package(get_package("msgpack-python", "0.5.3"))

    repo.add_package(get_package("pendulum", "2.0.3"))
    repo.add_package(get_package("cleo", "0.6.5"))


def test_debug_resolve_gives_resolution_results(tester: CommandTester):
    tester.execute("cachy")

    expected = """\
Resolving dependencies...

Resolution results:

msgpack-python 0.5.3
cachy          0.2.0
"""

    assert tester.io.fetch_output() == expected


def test_debug_resolve_tree_option_gives_the_dependency_tree(tester: CommandTester):
    tester.execute("cachy --tree")

    expected = """\
Resolving dependencies...

Resolution results:

cachy 0.2.0
└── msgpack-python >=0.5 <0.6
"""

    assert tester.io.fetch_output() == expected


def test_debug_resolve_git_dependency(tester: CommandTester):
    tester.execute("git+https://github.com/demo/demo.git")

    expected = """\
Resolving dependencies...

Resolution results:

pendulum 2.0.3
demo     0.1.2
"""

    assert tester.io.fetch_output() == expected
