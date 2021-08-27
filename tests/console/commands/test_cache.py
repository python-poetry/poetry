import uuid

<<<<<<< HEAD
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.monkeypatch import MonkeyPatch
    from cleo.testers.command_tester import CommandTester

    from tests.types import CommandTesterFactory


@pytest.fixture
def repository_cache_dir(monkeypatch: "MonkeyPatch", tmpdir: "Path") -> "Path":
=======
import pytest


@pytest.fixture
def repository_cache_dir(monkeypatch, tmpdir):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    from pathlib import Path

    import poetry.locations

    path = Path(str(tmpdir))
    monkeypatch.setattr(poetry.locations, "REPOSITORY_CACHE_DIR", path)
    return path


@pytest.fixture
<<<<<<< HEAD
def repository_one() -> str:
    return f"01_{uuid.uuid4()}"


@pytest.fixture
def repository_two() -> str:
    return f"02_{uuid.uuid4()}"


@pytest.fixture
def mock_caches(
    repository_cache_dir: "Path", repository_one: str, repository_two: str
) -> None:
=======
def repository_one():
    return "01_{}".format(uuid.uuid4())


@pytest.fixture
def repository_two():
    return "02_{}".format(uuid.uuid4())


@pytest.fixture
def mock_caches(repository_cache_dir, repository_one, repository_two):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    (repository_cache_dir / repository_one).mkdir()
    (repository_cache_dir / repository_two).mkdir()


@pytest.fixture
<<<<<<< HEAD
def tester(command_tester_factory: "CommandTesterFactory") -> "CommandTester":
    return command_tester_factory("cache list")


def test_cache_list(
    tester: "CommandTester", mock_caches: None, repository_one: str, repository_two: str
):
    tester.execute()

    expected = f"""\
{repository_one}
{repository_two}
"""
=======
def tester(command_tester_factory):
    return command_tester_factory("cache list")


def test_cache_list(tester, mock_caches, repository_one, repository_two):
    tester.execute()

    expected = """\
{}
{}
""".format(
        repository_one, repository_two
    )
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

    assert expected == tester.io.fetch_output()


<<<<<<< HEAD
def test_cache_list_empty(tester: "CommandTester", repository_cache_dir: "Path"):
=======
def test_cache_list_empty(tester, repository_cache_dir):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    tester.execute()

    expected = """\
No caches found
"""

    assert expected == tester.io.fetch_output()
