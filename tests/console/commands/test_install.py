<<<<<<< HEAD
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
    return command_tester_factory("install")


def test_group_options_are_passed_to_the_installer(
    tester: "CommandTester", mocker: "MockerFixture"
):
=======
import pytest


@pytest.fixture
def tester(command_tester_factory):
    return command_tester_factory("install")


def test_group_options_are_passed_to_the_installer(tester, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    """
    Group options are passed properly to the installer.
    """
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute("--with foo,bar --without baz --without bim --only bam")

    assert tester.command.installer._with_groups == ["foo", "bar"]
    assert tester.command.installer._without_groups == ["baz", "bim"]
    assert tester.command.installer._only_groups == ["bam"]


<<<<<<< HEAD
def test_sync_option_is_passed_to_the_installer(
    tester: "CommandTester", mocker: "MockerFixture"
):
=======
def test_sync_option_is_passed_to_the_installer(tester, mocker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    """
    The --sync option is passed properly to the installer.
    """
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute("--sync")

    assert tester.command.installer._requires_synchronization
