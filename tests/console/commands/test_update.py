from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.console.commands.update import UpdateCommand
from tests.helpers import get_package


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture
def poetry_with_outdated_lockfile(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Poetry:
    source = fixture_dir("outdated_lock")

    return project_factory(
        name="foobar",
        pyproject_content=(source / "pyproject.toml").read_text(encoding="utf-8"),
        poetry_lock_content=(source / "poetry.lock").read_text(encoding="utf-8"),
    )


@pytest.mark.parametrize(
    "command",
    [
        "--dry-run",
        "docker --dry-run",
    ],
)
def test_update_with_dry_run_keep_files_intact(
    command: str,
    poetry_with_outdated_lockfile: Poetry,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
) -> None:
    tester = command_tester_factory("update", poetry=poetry_with_outdated_lockfile)

    original_pyproject_content = poetry_with_outdated_lockfile.file.read()
    original_lockfile_content = poetry_with_outdated_lockfile._locker.lock_data

    repo.add_package(get_package("docker", "4.3.0"))
    repo.add_package(get_package("docker", "4.3.1"))

    tester.execute(command)

    assert poetry_with_outdated_lockfile.file.read() == original_pyproject_content
    assert poetry_with_outdated_lockfile._locker.lock_data == original_lockfile_content


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("", True),
        ("--dry-run", True),
        ("--lock", False),
    ],
)
def test_update_prints_operations(
    command: str,
    expected: bool,
    poetry_with_outdated_lockfile: Poetry,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
) -> None:
    tester = command_tester_factory("update", poetry=poetry_with_outdated_lockfile)

    repo.add_package(get_package("docker", "4.3.0"))
    repo.add_package(get_package("docker", "4.3.1"))

    tester.execute(command)
    output = tester.io.fetch_output()

    assert ("Package operations:" in output) is expected
    assert ("Installing docker (4.3.1)" in output) is expected


def test_update_sync_option_is_passed_to_the_installer(
    poetry_with_outdated_lockfile: Poetry,
    command_tester_factory: CommandTesterFactory,
    mocker: MockerFixture,
) -> None:
    """
    The --sync option is passed properly to the installer from update.
    """
    tester = command_tester_factory("update", poetry=poetry_with_outdated_lockfile)
    assert isinstance(tester.command, UpdateCommand)
    mocker.patch.object(tester.command.installer, "run", return_value=1)

    tester.execute("--sync")

    assert tester.command.installer._requires_synchronization
