from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.console.commands.self.install import SelfInstallCommand


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from tests.types import CommandTesterFactory


@pytest.fixture
def command() -> str:
    return "self install"


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory, command: str) -> CommandTester:
    return command_tester_factory(command)


@pytest.mark.parametrize(
    "pyproject_content",
    (
        None,
        """\
[tool.poetry]
name = "poetry-instance"
version = "1.2"
description = ""
authors = []
license = ""
# no package-mode -> defaults to true

[tool.poetry.dependencies]
python = "3.9"
poetry = "1.2"
""",
    ),
)
def test_self_install(
    tester: CommandTester,
    pyproject_content: str | None,
) -> None:
    command = tester.command
    assert isinstance(command, SelfInstallCommand)
    pyproject_path = command.system_pyproject
    if pyproject_content:
        pyproject_path.write_text(pyproject_content, encoding="utf-8")
    else:
        assert not pyproject_path.exists()

    tester.execute()

    expected_output = """\
Updating dependencies
Resolving dependencies...

Writing lock file
"""

    assert tester.io.fetch_output() == expected_output
    assert tester.io.fetch_error() == ""


@pytest.mark.parametrize("sync", [True, False])
def test_sync_deprecation(tester: CommandTester, sync: bool) -> None:
    tester.execute("--sync" if sync else "")

    error = tester.io.fetch_error()
    if sync:
        assert "deprecated" in error
        assert "poetry self sync" in error
    else:
        assert error == ""
