from pathlib import Path

import pytest

from poetry.packages import Locker
from tests.helpers import get_package


@pytest.fixture
def source_dir(tmp_path: Path) -> Path:
    yield Path(tmp_path.as_posix())


@pytest.fixture
def tester(command_tester_factory):
    return command_tester_factory("lock")


def _project_factory(fixture_name, project_factory, fixture_dir):
    source = fixture_dir(fixture_name)
    pyproject_content = (source / "pyproject.toml").read_text(encoding="utf-8")
    poetry_lock_content = (source / "poetry.lock").read_text(encoding="utf-8")
    return project_factory(
        name="foobar",
        pyproject_content=pyproject_content,
        poetry_lock_content=poetry_lock_content,
    )


@pytest.fixture
def poetry_with_outdated_lockfile(project_factory, fixture_dir):
    return _project_factory("outdated_lock", project_factory, fixture_dir)


@pytest.fixture
def poetry_with_up_to_date_lockfile(project_factory, fixture_dir):
    return _project_factory("up_to_date_lock", project_factory, fixture_dir)


@pytest.fixture
def poetry_with_old_lockfile(project_factory, fixture_dir):
    return _project_factory("old_lock", project_factory, fixture_dir)


def test_lock_check_outdated(
    command_tester_factory, poetry_with_outdated_lockfile, http
):
    http.disable()

    locker = Locker(
        lock=poetry_with_outdated_lockfile.pyproject.file.path.parent / "poetry.lock",
        local_config=poetry_with_outdated_lockfile.locker._local_config,
    )
    poetry_with_outdated_lockfile.set_locker(locker)

    tester = command_tester_factory("lock", poetry=poetry_with_outdated_lockfile)
    status_code = tester.execute("--check")

    # exit with an error
    assert status_code == 1


def test_lock_check_up_to_date(
    command_tester_factory, poetry_with_up_to_date_lockfile, http
):
    http.disable()

    locker = Locker(
        lock=poetry_with_up_to_date_lockfile.pyproject.file.path.parent / "poetry.lock",
        local_config=poetry_with_up_to_date_lockfile.locker._local_config,
    )
    poetry_with_up_to_date_lockfile.set_locker(locker)

    tester = command_tester_factory("lock", poetry=poetry_with_up_to_date_lockfile)
    status_code = tester.execute("--check")

    # exit with an error
    assert status_code == 0


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
