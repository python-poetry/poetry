from pathlib import Path

import pytest

from poetry.packages import Locker
from tests.helpers import get_package


@pytest.fixture
def source_dir(tmp_path):  # type: (Path) -> Path
    yield Path(tmp_path.as_posix())


@pytest.fixture
def tester(command_tester_factory):
    return command_tester_factory("lock")


@pytest.fixture
def poetry_with_old_lockfile(project_factory, fixture_dir, source_dir):
    source = fixture_dir("old_lock")
    pyproject_content = (source / "pyproject.toml").read_text(encoding="utf-8")
    poetry_lock_content = (source / "poetry.lock").read_text(encoding="utf-8")
    return project_factory(
        name="foobar",
        pyproject_content=pyproject_content,
        poetry_lock_content=poetry_lock_content,
    )


def test_lock_no_update(command_tester_factory, poetry_with_old_lockfile, repo):
    repo.add_package(get_package("sampleproject", "1.3.1"))
    repo.add_package(get_package("sampleproject", "2.0.0"))

    locker = Locker(
        lock=poetry_with_old_lockfile.pyproject.file.path.parent / "poetry.lock",
        local_config=poetry_with_old_lockfile.locker._local_config,
    )
    poetry_with_old_lockfile.set_locker(locker)

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
