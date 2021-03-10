from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.packages import Locker
from tests.helpers import get_package


if TYPE_CHECKING:
    from poetry.poetry import Poetry
    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture
def source_dir(tmp_path: Path) -> Path:
    return Path(tmp_path.as_posix())


@pytest.fixture
def poetry_with_old_lockfile(
    project_factory: "ProjectFactory", fixture_dir: "FixtureDirGetter"
) -> "Poetry":
    source = fixture_dir("old_lock")
    pyproject_content = (source / "pyproject.toml").read_text(encoding="utf-8")
    poetry_lock_content = (source / "poetry.lock").read_text(encoding="utf-8")
    return project_factory(
        name="foobar",
        pyproject_content=pyproject_content,
        poetry_lock_content=poetry_lock_content,
    )


def test_dry_run_update(
    command_tester_factory: "CommandTesterFactory",
    poetry_with_old_lockfile: "Poetry",
    repo: "TestRepository",
) -> None:
    repo.add_package(get_package("sampleproject", "1.3.1"))
    repo.add_package(get_package("sampleproject", "2.0.0"))

    lock = poetry_with_old_lockfile.pyproject.file.path.parent / "poetry.lock"
    locker = Locker(
        lock=lock,
        local_config=poetry_with_old_lockfile.locker._local_config,
    )
    poetry_with_old_lockfile.set_locker(locker)

    lock_content_before = lock.read_text(encoding="utf-8")

    tester = command_tester_factory("update", poetry=poetry_with_old_lockfile)
    tester.execute("--dry-run")

    assert lock.read_text(encoding="utf-8") == lock_content_before
