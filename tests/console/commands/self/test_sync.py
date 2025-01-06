from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cleo.exceptions import CleoNoSuchOptionError

# import all tests from the self install command
# and run them for sync by overriding the command fixture
from tests.console.commands.self.test_install import *  # noqa: F403


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture


@pytest.fixture  # type: ignore[no-redef]
def command() -> str:
    return "self sync"


@pytest.mark.skip("Only relevant for `poetry self install`")  # type: ignore[no-redef]
def test_sync_deprecation() -> None:
    """The only test from the self install command that does not work for self sync."""


def test_sync_option_not_available(tester: CommandTester) -> None:
    with pytest.raises(CleoNoSuchOptionError):
        tester.execute("--sync")


def test_synced_installer(tester: CommandTester, mocker: MockerFixture) -> None:
    mock = mocker.patch(
        "poetry.console.commands.install.InstallCommand._handle_install"
    )

    tester.execute()

    mock.assert_called_with(with_synchronization=True)
