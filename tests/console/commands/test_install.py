from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from tests.conftest import Config
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
    return command_tester_factory("install")


def test_group_options_are_passed_to_the_installer(
    tester: "CommandTester", mocker: "MockerFixture"
):
    """
    Group options are passed properly to the installer.
    """
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute("--with foo,bar --without baz --without bim --only bam")

    assert tester.command.installer._with_groups == ["foo", "bar"]
    assert tester.command.installer._without_groups == ["baz", "bim"]
    assert tester.command.installer._only_groups == ["bam"]


def test_sync_option_is_passed_to_the_installer(
    tester: "CommandTester", mocker: "MockerFixture"
):
    """
    The --sync option is passed properly to the installer.
    """
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute("--sync")

    assert tester.command.installer._requires_synchronization


def test_no_root(tester: "CommandTester", mocker: "MockerFixture"):
    mocker.patch.object(tester.command.installer, "run", return_value=0)
    from poetry.masonry.builders import EditableBuilder

    mock = mocker.patch.object(EditableBuilder, "__init__")
    tester.execute("--no-root")
    mock.assert_not_called()


def test_no_root_config(
    tester: "CommandTester", mocker: "MockerFixture", config: "Config"
):
    mocker.patch.object(tester.command.installer, "run", return_value=0)
    from poetry.masonry.builders import EditableBuilder

    mock = mocker.patch.object(EditableBuilder, "__init__")
    config.merge({"virtualenvs": {"no-root": True}})
    tester.execute("")
    mock.assert_not_called()
