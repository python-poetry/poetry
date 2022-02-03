from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
    return command_tester_factory("about")


def test_about(tester: "CommandTester"):
    tester.execute()
    expected = """\
Poetry - Package Management for Python

Poetry is a dependency manager tracking local dependencies of your projects and\
 libraries.
See https://github.com/python-poetry/poetry for more information.
"""

    assert tester.io.fetch_output() == expected
