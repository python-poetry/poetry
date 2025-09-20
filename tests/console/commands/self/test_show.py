from __future__ import annotations

import json

from typing import TYPE_CHECKING

import pytest
import tomlkit

from poetry.__version__ import __version__
from poetry.console.commands.self.self_command import SelfCommand


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("self show")


@pytest.mark.parametrize("options", ["", "--format json", "--format text"])
def test_show_format(tester: CommandTester, options: str) -> None:
    pyproject_content = {
        "tool": {
            "poetry": {
                "name": "poetry-instance",
                "version": __version__,
                "dependencies": {"python": "^3.9", "poetry": __version__},
            }
        }
    }
    lock_content = {
        "package": [
            {
                "name": "poetry",
                "version": __version__,
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "files": [],
            },
        ],
        "metadata": {
            "lock-version": "2.0",
            "python-versions": "^3.9",
            "content-hash": "123456789",
        },
    }
    if "json" in options:
        expected = json.dumps(
            [
                {
                    "name": "poetry",
                    "installed_status": "installed",
                    "version": __version__,
                    "description": "",
                }
            ]
        )
    else:
        expected = f"poetry {__version__}"
    system_pyproject_file = SelfCommand.get_default_system_pyproject_file()
    system_pyproject_file.write_text(tomlkit.dumps(pyproject_content), encoding="utf-8")
    system_pyproject_file.parent.joinpath("poetry.lock").write_text(
        tomlkit.dumps(lock_content), encoding="utf-8"
    )
    assert tester.execute(options) == 0
    assert tester.io.fetch_output().strip() == expected
