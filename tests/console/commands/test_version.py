from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.console.commands.version import VersionCommand


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from tests.types import CommandTesterFactory


@pytest.fixture()
def command() -> VersionCommand:
    return VersionCommand()


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("version")


@pytest.mark.parametrize(
    "version, rule, expected",
    [
        ("0.0.0", "patch", "0.0.1"),
        ("0.0.0", "minor", "0.1.0"),
        ("0.0.0", "major", "1.0.0"),
        ("0.0", "major", "1.0"),
        ("0.0", "minor", "0.1"),
        ("0.0", "patch", "0.0.1"),
        ("1.2.3", "patch", "1.2.4"),
        ("1.2.3", "minor", "1.3.0"),
        ("1.2.3", "major", "2.0.0"),
        ("1.2.3", "prepatch", "1.2.4a0"),
        ("1.2.3", "preminor", "1.3.0a0"),
        ("1.2.3", "premajor", "2.0.0a0"),
        ("1.2.3-beta.1", "patch", "1.2.3"),
        ("1.2.3-beta.1", "minor", "1.3.0"),
        ("1.2.3-beta.1", "major", "2.0.0"),
        ("1.2.3-beta.1", "prerelease", "1.2.3b2"),
        ("1.2.3-beta1", "prerelease", "1.2.3b2"),
        ("1.2.3beta1", "prerelease", "1.2.3b2"),
        ("1.2.3b1", "prerelease", "1.2.3b2"),
        ("1.2.3", "prerelease", "1.2.4a0"),
        ("0.0.0", "1.2.3", "1.2.3"),
    ],
)
def test_increment_version(
    version: str, rule: str, expected: str, command: VersionCommand
):
    assert command.increment_version(version, rule).text == expected


def test_version_show(tester: CommandTester):
    tester.execute()
    assert tester.io.fetch_output() == "simple-project 1.2.3\n"


def test_short_version_show(tester: CommandTester):
    tester.execute("--short")
    assert tester.io.fetch_output() == "1.2.3\n"


def test_version_update(tester: CommandTester):
    tester.execute("2.0.0")
    assert tester.io.fetch_output() == "Bumping version from 1.2.3 to 2.0.0\n"


def test_short_version_update(tester: CommandTester):
    tester.execute("--short 2.0.0")
    assert tester.io.fetch_output() == "2.0.0\n"


def test_dry_run(tester: CommandTester):
    old_pyproject = tester.command.poetry.file.path.read_text()
    tester.execute("--dry-run major")

    new_pyproject = tester.command.poetry.file.path.read_text()
    assert tester.io.fetch_output() == "Bumping version from 1.2.3 to 2.0.0\n"
    assert old_pyproject == new_pyproject
