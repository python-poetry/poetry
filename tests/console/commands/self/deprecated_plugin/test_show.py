from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("plugin show")


def test_deprecation_warning(tester: CommandTester) -> None:
    tester.execute("")
    assert (
        tester.io.fetch_error()
        == "This command is deprecated. Use self show plugins command instead.\n"
    )
