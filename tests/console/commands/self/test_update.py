from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.core.constraints.version import Version
from poetry.core.packages.package import Package

from poetry.__version__ import __version__
from poetry.factory import Factory


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory

FIXTURES = Path(__file__).parent.joinpath("fixtures")


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("self update")


def test_self_update_can_update_from_recommended_installation(
    tester: CommandTester,
    repo: TestRepository,
    installed: TestRepository,
):
    new_version = Version.parse(__version__).next_minor().text

    old_poetry = Package("poetry", __version__)
    old_poetry.add_dependency(Factory.create_dependency("cleo", "^0.8.2"))

    new_poetry = Package("poetry", new_version)
    new_poetry.add_dependency(Factory.create_dependency("cleo", "^1.0.0"))

    installed.add_package(old_poetry)
    installed.add_package(Package("cleo", "0.8.2"))

    repo.add_package(new_poetry)
    repo.add_package(Package("cleo", "1.0.0"))

    tester.execute()

    expected_output = f"""\
Updating Poetry version ...

Using version ^{new_version} for poetry

Updating dependencies
Resolving dependencies...

Writing lock file

Package operations: 0 installs, 2 updates, 0 removals

  • Updating cleo (0.8.2 -> 1.0.0)
  • Updating poetry ({__version__} -> {new_version})
"""

    assert tester.io.fetch_output() == expected_output
