import uuid

import pytest


@pytest.fixture
def repository_cache_dir(monkeypatch, tmpdir):
    from pathlib import Path

    import poetry.locations

    path = Path(str(tmpdir))
    monkeypatch.setattr(poetry.locations, "REPOSITORY_CACHE_DIR", path)
    return path


@pytest.fixture
def repository_one():
    return "01_{}".format(uuid.uuid4())


@pytest.fixture
def repository_two():
    return "02_{}".format(uuid.uuid4())


@pytest.fixture
def mock_caches(repository_cache_dir, repository_one, repository_two):
    (repository_cache_dir / repository_one).mkdir()
    (repository_cache_dir / repository_two).mkdir()


@pytest.fixture
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

    assert expected == tester.io.fetch_output()


def test_cache_list_empty(tester, repository_cache_dir):
    tester.execute()

    expected = """\
No caches found
"""

    assert expected == tester.io.fetch_output()
