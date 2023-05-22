from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("check")


def test_check_valid(tester: CommandTester) -> None:
    tester.execute()

    expected = """\
All set!
"""

    assert tester.io.fetch_output() == expected


def test_check_invalid(
    mocker: MockerFixture, tester: CommandTester, fixture_dir: FixtureDirGetter
) -> None:
    from poetry.toml import TOMLFile

    mocker.patch(
        "poetry.poetry.Poetry.file",
        return_value=TOMLFile(fixture_dir("invalid_pyproject") / "pyproject.toml"),
        new_callable=mocker.PropertyMock,
    )

    tester.execute()

    expected = """\
Error: 'description' is a required property
Error: Project name (invalid) is same as one of its dependencies
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


def test_check_private(
    mocker: MockerFixture, tester: CommandTester, fixture_dir: FixtureDirGetter
) -> None:
    mocker.patch(
        "poetry.factory.Factory.locate",
        return_value=fixture_dir("private_pyproject") / "pyproject.toml",
    )

    tester.execute()

    expected = """\
All set!
"""

    assert tester.io.fetch_output() == expected
