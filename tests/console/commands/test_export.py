from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from tests.conftest import Config
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("export")


def test_export_prints_warning(tester: CommandTester) -> None:
    tester.execute("")
    assert (
        "Warning: poetry-plugin-export will not be installed by default"
        in tester.io.fetch_error()
    )


def test_disable_export_warning(tester: CommandTester, config: Config) -> None:
    config.config["warnings"]["export"] = False
    tester.execute("")
    assert "poetry-plugin-export" not in tester.io.fetch_error()
