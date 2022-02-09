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


def test_no_editable_option(tester: "CommandTester", mocker: "MockerFixture"):
    mocker.patch.object(tester.command.installer, "run", return_value=0)
    pip_install_mock = mocker.patch("poetry.utils.pip.pip_install")
    builder_mock = mocker.patch("poetry.core.masonry.builders.sdist.SdistBuilder")
    editable_builder_mock = mocker.patch("poetry.masonry.builders.EditableBuilder")

    tester.execute("--no-editable")

    pip_install_mock.assert_called_once_with(
        path=tester.command.poetry.package.root_dir,
        environment=tester.command.env,
        deps=False,
        upgrade=True,
    )
    builder_mock.assert_called_once_with(tester.command.poetry)
    builder_mock.return_value.setup_py.assert_called_once()
    editable_builder_mock.assert_not_called()
