from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("check")


def test_check_valid(tester: CommandTester):
    tester.execute()

    expected = """\
All set!
"""

    assert tester.io.fetch_output() == expected


def test_check_invalid(mocker: MockerFixture, tester: CommandTester):
    mocker.patch(
        "poetry.factory.Factory.locate",
        return_value=Path(__file__).parent.parent.parent
        / "fixtures"
        / "invalid_pyproject"
        / "pyproject.toml",
    )

    tester.execute()

    expected = """\
Error: 'description' is a required property
Error: Unrecognized classifiers: ['Intended Audience :: Clowns'].
Warning: A wildcard Python dependency is ambiguous.\
 Consider specifying a more explicit one.
Warning: The "pendulum" dependency specifies the "allows-prereleases" property,\
 which is deprecated. Use "allow-prereleases" instead.
Warning: Deprecated classifier 'Natural Language :: Ukranian'.\
 Must be replaced by ['Natural Language :: Ukrainian'].
Warning: Deprecated classifier\
 'Topic :: Communications :: Chat :: AOL Instant Messenger'.\
 Must be removed.
"""

    assert tester.io.fetch_error() == expected
