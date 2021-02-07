import shutil

from pathlib import Path
from urllib.parse import urlparse

import pytest

from poetry.factory import Factory
from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.repositories.exceptions import PackageNotFound
from poetry.repositories.exceptions import RepositoryError
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.repositories.legacy_repository import Page


class MockRepository(LegacyRepository):

    FIXTURES = Path(__file__).parent / "fixtures" / "legacy"

    def __init__(self):
        super(MockRepository, self).__init__(
            "legacy", url="http://legacy.foo.bar", disable_cache=True
        )

    def _get(self, endpoint):
        parts = endpoint.split("/")
        name = parts[1]

        fixture = self.FIXTURES / (name + ".html")
        if not fixture.exists():
            return

        with fixture.open(encoding="utf-8") as f:
            return Page(self._url + endpoint, f.read(), {})

    def _download(self, url, dest):
        filename = urlparse(url).path.rsplit("/")[-1]
        filepath = self.FIXTURES.parent / "pypi.org" / "dists" / filename

        shutil.copyfile(str(filepath), dest)


class ErrorRepository(MockRepository):
    def _get(self, endpoint):
        raise RepositoryError()


def test_pool_raises_package_not_found_when_no_package_is_found():
    pool = Pool()
    pool.add_repository(Repository())

    with pytest.raises(PackageNotFound):
        pool.package("foo", "1.0.0")


def test_pool():
    pool = Pool()

    assert 0 == len(pool.repositories)
    assert not pool.has_default()


def test_pool_with_initial_repositories():
    repo = Repository()
    pool = Pool([repo])

    assert 1 == len(pool.repositories)
    assert not pool.has_default()


def test_repository_no_repository():
    pool = Pool()

    with pytest.raises(ValueError):
        pool.repository("foo")


def test_repository_from_normal_pool():
    repo = LegacyRepository("foo", "https://foo.bar")
    pool = Pool()
    pool.add_repository(repo)

    assert pool.repository("foo") is repo


def test_repository_from_secondary_pool():
    repo = LegacyRepository("foo", "https://foo.bar")
    pool = Pool()
    pool.add_repository(repo, secondary=True)

    assert pool.repository("foo") is repo


def test_repository_with_normal_default_and_secondary_repositories():
    secondary = LegacyRepository("secondary", "https://secondary.com")
    default = LegacyRepository("default", "https://default.com")
    repo1 = LegacyRepository("foo", "https://foo.bar")
    repo2 = LegacyRepository("bar", "https://bar.baz")

    pool = Pool()
    pool.add_repository(repo1)
    pool.add_repository(secondary, secondary=True)
    pool.add_repository(repo2)
    pool.add_repository(default, default=True)

    assert pool.repository("secondary") is secondary
    assert pool.repository("default") is default
    assert pool.repository("foo") is repo1
    assert pool.repository("bar") is repo2
    assert pool.has_default()


def test_default_repository_failure():
    default = ErrorRepository()
    secondary = MockRepository()
    pool = Pool()
    pool.add_repository(secondary, secondary=True)
    pool.add_repository(default, default=True)

    with pytest.raises(RepositoryError):
        pool.find_packages(Factory.create_dependency("pyyaml", "*"))


def test_secondary_repository_failure():
    secondary = ErrorRepository()
    default = MockRepository()
    pool = Pool()
    pool.add_repository(secondary, secondary=True)
    pool.add_repository(default, default=True)

    packages = pool.find_packages(Factory.create_dependency("pyyaml", "*"))

    assert len(packages) == 1
