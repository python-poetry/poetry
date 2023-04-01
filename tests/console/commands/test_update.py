from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.helpers import get_package


if TYPE_CHECKING:
    from poetry.poetry import Poetry
    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture
def poetry_with_up_to_date_lockfile(
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
    poetry_with_up_to_date_lockfile: Poetry,
    repo: TestRepository,
    command_tester_factory: CommandTesterFactory,
):
    tester = command_tester_factory("update", poetry=poetry_with_up_to_date_lockfile)

    original_pyproject_content = poetry_with_up_to_date_lockfile.file.read()
    original_lockfile_content = poetry_with_up_to_date_lockfile._locker.lock_data

    repo.add_package(get_package("docker", "4.3.0"))
    repo.add_package(get_package("docker", "4.3.1"))

    tester.execute(command)

    assert poetry_with_up_to_date_lockfile.file.read() == original_pyproject_content
    assert (
        poetry_with_up_to_date_lockfile._locker.lock_data == original_lockfile_content
    )
