import shutil
import sys

import pytest

from poetry.factory import Factory
from poetry.packages import Locker
from poetry.utils._compat import Path


@pytest.fixture
def source_dir(tmp_path):  # type: (Path) -> Path
    yield Path(tmp_path.as_posix())


@pytest.fixture
def tester(command_tester_factory):
    return command_tester_factory("lock")


@pytest.fixture
def poetry_with_old_lockfile(fixture_dir, source_dir):
    project_dir = source_dir / "project"
    shutil.copytree(str(fixture_dir("old_lock")), str(project_dir))
    poetry = Factory().create_poetry(cwd=project_dir)
    return poetry


@pytest.mark.skipif(
    sys.platform == "win32", reason="does not work on windows under ci environments"
)
def test_lock_no_update(command_tester_factory, poetry_with_old_lockfile, http):
    http.disable()

    locked_repository = poetry_with_old_lockfile.locker.locked_repository(
        with_dev_reqs=True
    )
    assert (
        poetry_with_old_lockfile.locker.lock_data["metadata"].get("lock-version")
        == "1.0"
    )

    tester = command_tester_factory("lock", poetry=poetry_with_old_lockfile)
    tester.execute("--no-update")

    locker = Locker(
        lock=poetry_with_old_lockfile.pyproject.file.path.parent / "poetry.lock",
        local_config={},
    )
    packages = locker.locked_repository(True).packages

    assert len(packages) == len(locked_repository.packages)

    assert locker.lock_data["metadata"].get("lock-version") == "1.1"

    for package in packages:
        assert locked_repository.find_packages(package.to_dependency())
