from __future__ import annotations
from struct import pack

import pytest

from copy import deepcopy

from poetry.core.packages.package import Package

from poetry.repositories.lockfile_repository import LockfileRepository


@pytest.fixture(scope="module")
def packages():
    return [
        Package(
            "a", "1.0", source_type="url", source_url="https://example.org/a.whl"
        ),
        Package("a", "1.0"),
        Package(
            "a", "1.0", source_type="url", source_url="https://example.org/a-1.whl"
        )
    ]


def test_has_package(packages):
    url_package, pypi_package, url_package_2 = packages
    repo = LockfileRepository()

    assert not repo.has_package(url_package)
    repo.add_package(url_package)

    assert not repo.has_package(pypi_package)
    repo.add_package(pypi_package)

    assert not repo.has_package(url_package_2)
    repo.add_package(url_package_2)

    assert len(repo.packages) == 3
    assert repo.has_package(deepcopy(url_package))
    assert repo.has_package(deepcopy(pypi_package))
    assert repo.has_package(deepcopy(url_package_2))


def test_remove_package(packages):
    url_package, pypi_package, url_package_2 = packages

    repo = LockfileRepository()
    repo.add_package(url_package)
    repo.add_package(pypi_package)
    repo.add_package(url_package_2)

    assert len(repo.packages) == 3

    repo.remove_package(deepcopy(pypi_package))
    assert len(repo.packages) == 2
    repo.remove_package(pypi_package)
    assert len(repo.packages) == 2

    repo.remove_package(deepcopy(url_package_2))
    assert len(repo.packages) == 1
    assert repo.packages[0] == url_package
    repo.remove_package(url_package_2)
    assert len(repo.packages) == 1
