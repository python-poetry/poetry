from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.core.packages.package import Package

from poetry.__version__ import __version__


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("plugin add")


def test_deprecation_warning(tester: CommandTester, repo: TestRepository) -> None:
    repo.add_package(Package("poetry", __version__))
    repo.add_package(Package("poetry-plugin", "1.0"))
    tester.execute("poetry-plugin")
    assert (
        tester.io.fetch_error()
        == "This command is deprecated. Use self add command instead.\n"
    )
