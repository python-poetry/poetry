from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.core.constraints.version import Version
from poetry.core.packages.package import Package

from poetry.__version__ import __version__
from poetry.factory import Factory
from poetry.installation.executor import Executor
from poetry.installation.wheel_installer import WheelInstaller


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter


@pytest.fixture
def setup(mocker: MockerFixture, fixture_dir: FixtureDirGetter) -> None:
    mocker.patch.object(
        Executor,
        "_download",
        return_value=fixture_dir("distributions").joinpath(
            "demo-0.1.2-py2.py3-none-any.whl"
        ),
    )

    mocker.patch.object(WheelInstaller, "install")


@pytest.fixture()
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("self update")


def test_self_update_can_update_from_recommended_installation(
    tester: CommandTester,
    repo: TestRepository,
    installed: TestRepository,
) -> None:
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

Package operations: 0 installs, 2 updates, 0 removals

  - Updating cleo (0.8.2 -> 1.0.0)
  - Updating poetry ({__version__} -> {new_version})

Writing lock file
"""

    assert tester.io.fetch_output() == expected_output
