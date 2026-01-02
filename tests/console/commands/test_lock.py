from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.core.constraints.version import Version

from poetry.packages import Locker
from tests.helpers import get_package


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.poetry import Poetry
    from tests.helpers import TestRepository
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture
def source_dir(tmp_path: Path) -> Path:
    return Path(tmp_path.as_posix())


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("lock")


def _project_factory(
    fixture_name: str,
    project_factory: ProjectFactory,
    fixture_dir: FixtureDirGetter,
) -> Poetry:
    source = fixture_dir(fixture_name)
    pyproject_content = (source / "pyproject.toml").read_text(encoding="utf-8")
    poetry_lock_content = (source / "poetry.lock").read_text(encoding="utf-8")
    return project_factory(
        name="foobar",
        pyproject_content=pyproject_content,
        poetry_lock_content=poetry_lock_content,
        source=source,
    )


@pytest.fixture
def poetry_with_outdated_lockfile(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Poetry:
    return _project_factory("outdated_lock", project_factory, fixture_dir)


@pytest.fixture
def poetry_with_up_to_date_lockfile(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Poetry:
    return _project_factory("up_to_date_lock", project_factory, fixture_dir)


@pytest.fixture
def poetry_with_old_lockfile(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Poetry:
    return _project_factory("old_lock", project_factory, fixture_dir)


@pytest.fixture
def poetry_with_nested_path_deps_old_lockfile(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Poetry:
    return _project_factory("old_lock_path_dependency", project_factory, fixture_dir)


@pytest.fixture
def poetry_with_incompatible_lockfile(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Poetry:
    return _project_factory("incompatible_lock", project_factory, fixture_dir)


@pytest.fixture
def poetry_with_invalid_lockfile(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Poetry:
    return _project_factory("invalid_lock", project_factory, fixture_dir)


def test_lock_does_not_update_if_not_necessary(
    command_tester_factory: CommandTesterFactory,
    poetry_with_old_lockfile: Poetry,
    repo: TestRepository,
) -> None:
    package = get_package("sampleproject", "1.3.1")
    repo.add_package(package)
    repo.add_package(get_package("sampleproject", "2.0.0"))

    locker = Locker(
        lock=poetry_with_old_lockfile.pyproject.file.path.parent / "poetry.lock",
        pyproject_data=poetry_with_old_lockfile.locker._pyproject_data,
    )
    poetry_with_old_lockfile.set_locker(locker)

    locked_repository = poetry_with_old_lockfile.locker.locked_repository()
    assert (
        poetry_with_old_lockfile.locker.lock_data["metadata"].get("lock-version")
        == "1.0"
    )

    # set correct files to avoid cache refresh
    package.files = (
        locker.locked_repository()
        .package("sampleproject", Version.parse("1.3.1"))
        .files
    )

    tester = command_tester_factory("lock", poetry=poetry_with_old_lockfile)
    tester.execute()

    locker = Locker(
        lock=poetry_with_old_lockfile.pyproject.file.path.parent / "poetry.lock",
        pyproject_data={},
    )
    packages = locker.locked_repository().packages

    assert len(packages) == len(locked_repository.packages)

    assert locker.lock_data["metadata"].get("lock-version") == "2.1"

    for package in packages:
        assert locked_repository.find_packages(package.to_dependency())


@pytest.mark.parametrize("regenerate", [True, False])
def test_lock_always_updates_path_dependencies(
    command_tester_factory: CommandTesterFactory,
    poetry_with_nested_path_deps_old_lockfile: Poetry,
    repo: TestRepository,
    regenerate: bool,
) -> None:
    """
    The lock file contains a variant of the directory dependency "quix" that does
    not depend on "sampleproject". Although the version of "quix" has not been changed,
    it should be re-solved because there is always only one valid version
    of a directory dependency at any time.
    """
    repo.add_package(get_package("sampleproject", "1.3.1"))

    locker = Locker(
        lock=poetry_with_nested_path_deps_old_lockfile.pyproject.file.path.parent
        / "poetry.lock",
        pyproject_data=poetry_with_nested_path_deps_old_lockfile.locker._pyproject_data,
    )
    poetry_with_nested_path_deps_old_lockfile.set_locker(locker)

    tester = command_tester_factory(
        "lock", poetry=poetry_with_nested_path_deps_old_lockfile
    )
    tester.execute("--regenerate" if regenerate else "")

    packages = locker.locked_repository().packages

    assert {p.name for p in packages} == {"quix", "sampleproject"}


@pytest.mark.parametrize("regenerate", [True, False])
@pytest.mark.parametrize(
    "project", ["missing_directory_dependency", "missing_file_dependency"]
)
def test_lock_path_dependency_does_not_exist(
    command_tester_factory: CommandTesterFactory,
    project_factory: ProjectFactory,
    fixture_dir: FixtureDirGetter,
    project: str,
    regenerate: bool,
) -> None:
    poetry = _project_factory(project, project_factory, fixture_dir)
    locker = Locker(
        lock=poetry.pyproject.file.path.parent / "poetry.lock",
        pyproject_data=poetry.locker._pyproject_data,
    )
    poetry.set_locker(locker)
    options = "--regenerate" if regenerate else ""

    tester = command_tester_factory("lock", poetry=poetry)
    if regenerate or "directory" in project:
        # directory dependencies are always updated
        with pytest.raises(ValueError, match="does not exist"):
            tester.execute(options)
    else:
        tester.execute(options)


@pytest.mark.parametrize("regenerate", [True, False])
@pytest.mark.parametrize(
    "project", ["deleted_directory_dependency", "deleted_file_dependency"]
)
def test_lock_path_dependency_deleted_from_pyproject(
    command_tester_factory: CommandTesterFactory,
    project_factory: ProjectFactory,
    fixture_dir: FixtureDirGetter,
    project: str,
    regenerate: bool,
) -> None:
    poetry = _project_factory(project, project_factory, fixture_dir)
    locker = Locker(
        lock=poetry.pyproject.file.path.parent / "poetry.lock",
        pyproject_data=poetry.locker._pyproject_data,
    )
    poetry.set_locker(locker)

    tester = command_tester_factory("lock", poetry=poetry)
    tester.execute("--regenerate" if regenerate else "")

    packages = locker.locked_repository().packages

    assert {p.name for p in packages} == set()


@pytest.mark.parametrize("regenerate", [True, False])
def test_lock_with_incompatible_lockfile(
    command_tester_factory: CommandTesterFactory,
    poetry_with_incompatible_lockfile: Poetry,
    repo: TestRepository,
    regenerate: bool,
) -> None:
    repo.add_package(get_package("sampleproject", "1.3.1"))

    locker = Locker(
        lock=poetry_with_incompatible_lockfile.pyproject.file.path.parent
        / "poetry.lock",
        pyproject_data=poetry_with_incompatible_lockfile.locker._pyproject_data,
    )
    poetry_with_incompatible_lockfile.set_locker(locker)

    tester = command_tester_factory("lock", poetry=poetry_with_incompatible_lockfile)
    if regenerate:
        # still possible because lock file is not required
        status_code = tester.execute("--regenerate")
        assert status_code == 0
    else:
        # not possible because of incompatible lock file
        expected = (
            "(?s)lock file is not compatible .*"
            " regenerate the lock file with the `poetry lock` command"
        )
        with pytest.raises(RuntimeError, match=expected):
            tester.execute()


@pytest.mark.parametrize("regenerate", [True, False])
def test_lock_with_invalid_lockfile(
    command_tester_factory: CommandTesterFactory,
    poetry_with_invalid_lockfile: Poetry,
    repo: TestRepository,
    regenerate: bool,
) -> None:
    repo.add_package(get_package("sampleproject", "1.3.1"))

    locker = Locker(
        lock=poetry_with_invalid_lockfile.pyproject.file.path.parent / "poetry.lock",
        pyproject_data=poetry_with_invalid_lockfile.locker._pyproject_data,
    )
    poetry_with_invalid_lockfile.set_locker(locker)

    tester = command_tester_factory("lock", poetry=poetry_with_invalid_lockfile)
    if regenerate:
        # still possible because lock file is not required
        status_code = tester.execute("--regenerate")
        assert status_code == 0
    else:
        # not possible because of broken lock file
        with pytest.raises(RuntimeError, match="Unable to read the lock file"):
            tester.execute()
