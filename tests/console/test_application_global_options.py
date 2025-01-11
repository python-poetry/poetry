from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cleo.testers.application_tester import ApplicationTester

from poetry.console.application import Application


if TYPE_CHECKING:
    from tests.types import FixtureCopier


NO_PYPROJECT_TOML_ERROR = "Poetry could not find a pyproject.toml file in"


@pytest.fixture
def project_source_directory(fixture_copier: FixtureCopier) -> Path:
    return fixture_copier("up_to_date_lock")


@pytest.fixture
def tester() -> ApplicationTester:
    return ApplicationTester(Application())


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
