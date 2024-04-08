from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.console.commands.version import VersionCommand


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture()
def command() -> VersionCommand:
    return VersionCommand()


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("version")


@pytest.fixture
def poetry_with_underscore(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Poetry:
    source = fixture_dir("simple_project")
    pyproject_content = (source / "pyproject.toml").read_text(encoding="utf-8")
    pyproject_content = pyproject_content.replace("simple-project", "simple_project")
    return project_factory(
        "project_with_underscore", pyproject_content=pyproject_content
    )


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
) -> None:
    assert command.increment_version(version, rule).text == expected


@pytest.mark.parametrize(
    "version, rule, expected",
    [
        ("1.2.3", "prerelease", "1.2.4a0"),
        ("1.2.3a0", "prerelease", "1.2.3b0"),
        ("1.2.3a1", "prerelease", "1.2.3b0"),
        ("1.2.3b1", "prerelease", "1.2.3rc0"),
        ("1.2.3rc0", "prerelease", "1.2.3"),
        ("1.2.3-beta.1", "prerelease", "1.2.3rc0"),
        ("1.2.3-beta1", "prerelease", "1.2.3rc0"),
        ("1.2.3beta1", "prerelease", "1.2.3rc0"),
    ],
)
def test_next_phase_version(
    version: str, rule: str, expected: str, command: VersionCommand
) -> None:
    assert command.increment_version(version, rule, True).text == expected


def test_version_show(tester: CommandTester) -> None:
    tester.execute()
    assert tester.io.fetch_output() == "simple-project 1.2.3\n"


def test_version_show_with_underscore(
    command_tester_factory: CommandTesterFactory, poetry_with_underscore: Poetry
) -> None:
    tester = command_tester_factory("version", poetry=poetry_with_underscore)
    tester.execute()
    assert tester.io.fetch_output() == "simple_project 1.2.3\n"


def test_short_version_show(tester: CommandTester) -> None:
    tester.execute("--short")
    assert tester.io.fetch_output() == "1.2.3\n"


def test_version_update(tester: CommandTester) -> None:
    tester.execute("2.0.0")
    assert tester.io.fetch_output() == "Bumping version from 1.2.3 to 2.0.0\n"


def test_short_version_update(tester: CommandTester) -> None:
    tester.execute("--short 2.0.0")
    assert tester.io.fetch_output() == "2.0.0\n"


def test_phase_version_update(tester: CommandTester) -> None:
    assert isinstance(tester.command, VersionCommand)
    tester.command.poetry.package._set_version("1.2.4a0")
    tester.execute("prerelease --next-phase")
    assert tester.io.fetch_output() == "Bumping version from 1.2.4a0 to 1.2.4b0\n"


def test_dry_run(tester: CommandTester) -> None:
    assert isinstance(tester.command, VersionCommand)
    old_pyproject = tester.command.poetry.file.path.read_text()
    tester.execute("--dry-run major")

    new_pyproject = tester.command.poetry.file.path.read_text()
    assert tester.io.fetch_output() == "Bumping version from 1.2.3 to 2.0.0\n"
    assert old_pyproject == new_pyproject
