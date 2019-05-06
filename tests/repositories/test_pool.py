import pytest

from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.repositories.exceptions import PackageNotFound
from poetry.packages import Package

class MockRepository(Repository):

    def __init__(self, name, **kwargs):
        super(MockRepository, self).__init__(**kwargs)
        self._name = name

    @property
    def name(self):
        return self._name


def test_pool_raises_package_not_found_when_no_package_is_found():
    pool = Pool()
    pool.add_repository(Repository())

    with pytest.raises(PackageNotFound):
        pool.package("foo", "1.0.0")


def test_find_packages_with_specified_repository():
    package = Package('test', '1.0')
    repo_1 = MockRepository('foo', packages=[])
    repo_2 = MockRepository('PyPI', packages=[package])
    pool = Pool()
    pool.add_repository(repo_1)
    pool.add_repository(repo_2)

    assert pool.find_packages('test') == [package]
    assert pool.find_packages('test', repository_name='PyPI') == [package]
    assert pool.find_packages('test', repository_name='foo') == []
