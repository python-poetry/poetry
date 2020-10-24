import shutil

from pathlib import Path

import pytest

from poetry.factory import Factory


@pytest.fixture
def source_dir(tmp_path):  # type: (Path) -> Path
    yield Path(tmp_path.as_posix())


@pytest.fixture
def poetry_with_old_lockfile(fixture_dir, source_dir):
    project_dir = source_dir / "project"
    shutil.copytree(str(fixture_dir("old_lock")), str(project_dir))
    poetry = Factory().create_poetry(cwd=project_dir)
    return poetry


@pytest.fixture
def tester(command_tester_factory, poetry_with_old_lockfile):
    return command_tester_factory("update", poetry=poetry_with_old_lockfile)


def test_update(tester, poetry_with_old_lockfile, http):
    http.disable()
    tester.execute()
    assert (
        poetry_with_old_lockfile.locker.lock_data["metadata"]["lock-version"] == "1.1"
    )
    assert "Updating dependencies" in tester.io.fetch_output()
    assert "Resolving dependencies" in tester.io.fetch_output()
    assert "Writing lock file" in tester.io.fetch_output()
