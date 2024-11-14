from __future__ import annotations

import os
import textwrap

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cleo.testers.application_tester import ApplicationTester

from poetry.console.application import Application
from poetry.console.commands.version import VersionCommand


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

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
    old_pyproject = tester.command.poetry.file.path.read_text(encoding="utf-8")
    tester.execute("--dry-run major")

    new_pyproject = tester.command.poetry.file.path.read_text(encoding="utf-8")
    assert tester.io.fetch_output() == "Bumping version from 1.2.3 to 2.0.0\n"
    assert old_pyproject == new_pyproject


def test_version_with_project_parameter(
    fixture_dir: FixtureDirGetter, mocker: MockerFixture
) -> None:
    app = Application()
    tester = ApplicationTester(app)

    orig_version_command = VersionCommand.handle

    def mock_handle(command: VersionCommand) -> int:
        exit_code = orig_version_command(command)

        command.io.write_line(f"ProjectPath: {command.poetry.pyproject_path.parent}")
        command.io.write_line(f"WorkingDirectory: {os.getcwd()}")

        return exit_code

    mocker.patch("poetry.console.commands.version.VersionCommand.handle", mock_handle)

    source_dir = fixture_dir("scripts")
    tester.execute(f"--project {source_dir} version")

    output = tester.io.fetch_output()
    expected = textwrap.dedent(f"""\
    scripts 0.1.0
    ProjectPath: {source_dir}
    WorkingDirectory: {os.getcwd()}
    """)

    assert source_dir != Path(os.getcwd())
    assert output == expected


def test_version_with_directory_parameter(
    fixture_dir: FixtureDirGetter, mocker: MockerFixture
) -> None:
    app = Application()
    tester = ApplicationTester(app)

    orig_version_command = VersionCommand.handle

    def mock_handle(command: VersionCommand) -> int:
        exit_code = orig_version_command(command)

        command.io.write_line(f"ProjectPath: {command.poetry.pyproject_path.parent}")
        command.io.write_line(f"WorkingDirectory: {os.getcwd()}")

        return exit_code

    mocker.patch("poetry.console.commands.version.VersionCommand.handle", mock_handle)

    source_dir = fixture_dir("scripts")
    tester.execute(f"--directory {source_dir} version")

    output = tester.io.fetch_output()
    expected = textwrap.dedent(f"""\
    scripts 0.1.0
    ProjectPath: {source_dir}
    WorkingDirectory: {source_dir}
    """)

    assert source_dir != Path(os.getcwd())
    assert output == expected


def test_version_with_directory_and_project_parameter(
    fixture_dir: FixtureDirGetter, mocker: MockerFixture
) -> None:
    app = Application()
    tester = ApplicationTester(app)

    orig_version_command = VersionCommand.handle

    def mock_handle(command: VersionCommand) -> int:
        exit_code = orig_version_command(command)

        command.io.write_line(f"ProjectPath: {command.poetry.pyproject_path.parent}")
        command.io.write_line(f"WorkingDirectory: {os.getcwd()}")

        return exit_code

    mocker.patch("poetry.console.commands.version.VersionCommand.handle", mock_handle)

    source_dir = fixture_dir("scripts")
    working_directory = source_dir.parent
    project_path = "./scripts"

    tester.execute(f"--directory {working_directory} --project {project_path} version")

    output = tester.io.fetch_output()

    expected = textwrap.dedent(f"""\
    scripts 0.1.0
    ProjectPath: {source_dir}
    WorkingDirectory: {working_directory}
    """)

    assert source_dir != working_directory
    assert output == expected
