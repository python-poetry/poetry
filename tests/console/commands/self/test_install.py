from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.console.commands.self.install import SelfInstallCommand


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("self install")


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
        pyproject_path.write_text(pyproject_content)
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
