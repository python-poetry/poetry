import uuid

import pytest

from cleo.testers import CommandTester


@pytest.fixture
def repository_cache_dir(monkeypatch, tmpdir):
    import poetry.locations

    from poetry.utils._compat import Path

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


def test_cache_list(app, mock_caches, repository_one, repository_two):
    command = app.find("cache list")
    tester = CommandTester(command)

    tester.execute()

    expected = """\
{}
{}
""".format(
        repository_one, repository_two
    )

    assert expected == tester.io.fetch_output()


def test_cache_list_empty(app, repository_cache_dir):
    command = app.find("cache list")
    tester = CommandTester(command)

    tester.execute()

    expected = """\
No caches found
"""

    assert expected == tester.io.fetch_output()
