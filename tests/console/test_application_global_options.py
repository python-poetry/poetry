from __future__ import annotations

import re
import textwrap

from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar

import pytest

from cleo.io.buffered_io import BufferedIO
from cleo.io.inputs.string_input import StringInput
from cleo.testers.application_tester import ApplicationTester

from poetry.console.application import Application
from poetry.console.commands.command import Command
from poetry.console.commands.version import VersionCommand
from poetry.plugins import ApplicationPlugin
from tests.helpers import mock_metadata_entry_points
from tests.helpers import switch_working_directory


if TYPE_CHECKING:
    from pytest import TempPathFactory
    from pytest_mock import MockerFixture

    from tests.types import FixtureCopier


NO_PYPROJECT_TOML_ERROR = "Poetry could not find a pyproject.toml file in"


class CheckProjectPathCommand(Command):
    name = "check-project-path"

    description = "Check Project Path Command"

    def handle(self) -> int:
        if not self.poetry.pyproject_path.exists():
            raise RuntimeError(
                f"Wrong project path in handle: {self.poetry.pyproject_path}\nWorking directory: {Path.cwd()}"
            )

        return 0


class EarlyPoetryAccessPlugin(ApplicationPlugin):
    commands: ClassVar[list[type[Command]]] = [CheckProjectPathCommand]

    def activate(self, application: Application) -> None:
        super().activate(application)

        # access application.poetry
        # see https://github.com/nat-n/poethepoet/issues/288
        if not application.poetry.pyproject_path.exists():
            raise RuntimeError(
                f"Wrong project path in activate: {application.poetry.pyproject_path}\nWorking directory: {Path.cwd()}"
            )


@pytest.fixture
def with_early_poetry_access_plugin(mocker: MockerFixture) -> None:
    mock_metadata_entry_points(mocker, EarlyPoetryAccessPlugin)


@pytest.fixture
def project_source_directory(fixture_copier: FixtureCopier) -> Path:
    return fixture_copier("up_to_date_lock")


@pytest.fixture
def relative_project_source_directory(project_source_directory: Path) -> Path:
    # ensure pre-conditions are met
    cwd = Path.cwd()
    assert project_source_directory.is_relative_to(cwd)

    # construct relative path
    relative_source_directory = project_source_directory.relative_to(cwd)
    assert relative_source_directory.as_posix() != project_source_directory.as_posix()
    assert not relative_source_directory.is_absolute()

    return relative_source_directory


@pytest.fixture
def tester() -> ApplicationTester:
    return ApplicationTester(Application())


@pytest.fixture
def with_mocked_version_command(mocker: MockerFixture) -> None:
    orig_version_command = VersionCommand.handle

    def mock_handle(command: VersionCommand) -> int:
        exit_code = orig_version_command(command)

        command.io.write_line(f"ProjectPath: {command.poetry.pyproject_path.parent}")
        command.io.write_line(f"WorkingDirectory: {Path.cwd()}")

        return exit_code

    mocker.patch("poetry.console.commands.version.VersionCommand.handle", mock_handle)


def test_application_global_option_ensure_error_when_context_invalid(
    tester: ApplicationTester,
) -> None:
    # command fails due to lack of pyproject.toml file in cwd
    tester.execute("show --only main")
    assert tester.status_code != 0

    stderr = tester.io.fetch_error()
    assert NO_PYPROJECT_TOML_ERROR in stderr


@pytest.mark.parametrize("parameter", ["-C", "--directory", "-P", "--project"])
@pytest.mark.parametrize(
    "command_args",
    [
        "{option} show --only main",
        "show {option} --only main",
        "show --only main {option}",
    ],
)
def test_application_global_option_position_does_not_matter(
    parameter: str,
    command_args: str,
    tester: ApplicationTester,
    project_source_directory: Path,
) -> None:
    cwd = Path.cwd()
    assert cwd != project_source_directory

    option = f"{parameter} {project_source_directory.as_posix()}"
    tester.execute(command_args.format(option=option))
    assert tester.status_code == 0

    stdout = tester.io.fetch_output()
    stderr = tester.io.fetch_error()

    assert NO_PYPROJECT_TOML_ERROR not in stderr
    assert NO_PYPROJECT_TOML_ERROR not in stdout

    assert "certifi" in stdout
    assert len(stdout.splitlines()) == 8


@pytest.mark.parametrize("parameter", ["-C", "--directory", "-P", "--project"])
@pytest.mark.parametrize(
    "invalid_source_directory",
    [
        "/invalid/path",  # non-existent path
        __file__,  # not a directory
    ],
)
def test_application_global_option_context_is_validated(
    parameter: str,
    tester: ApplicationTester,
    invalid_source_directory: str,
) -> None:
    option = f"{parameter} '{invalid_source_directory}'"
    tester.execute(f"show {option}")
    assert tester.status_code != 0

    stdout = tester.io.fetch_output()
    assert stdout == ""

    stderr = tester.io.fetch_error()
    assert re.match(
        r"\nSpecified path '(.+)?' is not a valid directory.\n",
        stderr,
    )


@pytest.mark.parametrize("parameter", ["project", "directory"])
def test_application_with_context_parameters(
    parameter: str,
    tester: ApplicationTester,
    project_source_directory: Path,
    with_mocked_version_command: None,
) -> None:
    # ensure pre-conditions are met
    assert project_source_directory != Path.cwd()

    is_directory_param = parameter == "directory"

    tester.execute(f"--{parameter} {project_source_directory} version")
    assert tester.io.fetch_error() == ""
    assert tester.status_code == 0

    output = tester.io.fetch_output()
    assert output == textwrap.dedent(f"""\
    foobar 0.1.0
    ProjectPath: {project_source_directory}
    WorkingDirectory: {project_source_directory if is_directory_param else Path.cwd()}
    """)


def test_application_with_relative_project_parameter(
    tester: ApplicationTester,
    project_source_directory: Path,
    relative_project_source_directory: Path,
    with_mocked_version_command: None,
    tmp_path_factory: TempPathFactory,
) -> None:
    cwd = Path.cwd()
    # we expect application run to be executed within current cwd
    # but project to be a subdirectory
    args = f"--directory '{cwd}' --project {relative_project_source_directory} version"

    # we switch cwd to a new temporary directory unrelated to the project directory
    new_working_dir = tmp_path_factory.mktemp("unrelated-working-directory")
    with switch_working_directory(new_working_dir):
        assert Path.cwd() == new_working_dir

        tester.execute(args)
        assert tester.io.fetch_error() == ""
        assert tester.status_code == 0

        output = tester.io.fetch_output()
        assert output == textwrap.dedent(f"""\
        foobar 0.1.0
        ProjectPath: {project_source_directory}
        WorkingDirectory: {cwd}
        """)


def test_application_with_relative_directory_parameter_and_early_poetry_access_plugin(
    tester: ApplicationTester,
    with_early_poetry_access_plugin: None,
    relative_project_source_directory: Path,
) -> None:
    """see https://github.com/nat-n/poethepoet/issues/288"""
    tester.execute(
        f"--directory {relative_project_source_directory} check-project-path"
    )

    assert tester.status_code == 0, tester.io.fetch_error()


@pytest.mark.parametrize(
    ("parameter", "check", "result"),
    [
        ("--ansi", "is_decorated", True),
        ("--no-ansi", "is_decorated", False),
        ("--no-interaction", "is_interactive", False),
        ("--verbose", "is_verbose", True),
        ("-vv", "is_verbose", True),
        ("-vv", "is_very_verbose", True),
        ("-vv", "is_debug", False),
        ("-vvv", "is_debug", True),
    ],
)
def test_application_io_options_are_set(
    parameter: str, check: str, result: bool
) -> None:
    # we use an actual application here to avoid cleo's testing overrides
    application = Application()
    application.auto_exits(False)
    application._io = BufferedIO()

    assert application.run(StringInput(f"{parameter} about")) == 0
    assert getattr(application._io, check)() == result
