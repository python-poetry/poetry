from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from poetry.factory import Factory
from poetry.mixology.version_solver import DependencyCache
from tests.helpers import MOCK_DEFAULT_GIT_REVISION
from tests.mixology.helpers import add_to_repo


if TYPE_CHECKING:
    from poetry.core.packages.project_package import ProjectPackage

    from poetry.repositories import Repository
    from tests.mixology.version_solver.conftest import Provider


def test_solver_dependency_cache_respects_source_type(
    root: ProjectPackage, provider: Provider, repo: Repository
):
    dependency_pypi = Factory.create_dependency("demo", ">=0.1.0")
    dependency_git = Factory.create_dependency(
        "demo", {"git": "https://github.com/demo/demo.git"}, groups=["dev"]
    )
    root.add_dependency(dependency_pypi)
    root.add_dependency(dependency_git)

    add_to_repo(repo, "demo", "1.0.0")

    cache = DependencyCache(provider)
    cache.search_for.cache_clear()

    # ensure cache was never hit for both calls
    cache.search_for(dependency_pypi)
    cache.search_for(dependency_git)
    assert not cache.search_for.cache_info().hits

    # increase test coverage by searching for copies
    # (when searching for the exact same object, __eq__ is never called)
    packages_pypi = cache.search_for(deepcopy(dependency_pypi))
    packages_git = cache.search_for(deepcopy(dependency_git))

    assert cache.search_for.cache_info().hits == 2
    assert cache.search_for.cache_info().currsize == 2

    assert len(packages_pypi) == len(packages_git) == 1
    assert packages_pypi != packages_git

    package_pypi = packages_pypi[0]
    package_git = packages_git[0]

    assert package_pypi.package.name == dependency_pypi.name
    assert package_pypi.package.version.text == "1.0.0"

    assert package_git.package.name == dependency_git.name
    assert package_git.package.version.text == "0.1.2"
    assert package_git.package.source_type == dependency_git.source_type
    assert package_git.package.source_url == dependency_git.source_url
    assert package_git.package.source_resolved_reference == MOCK_DEFAULT_GIT_REVISION


def test_solver_dependency_cache_respects_subdirectories(
    root: ProjectPackage, provider: Provider, repo: Repository
):
    dependency_one = Factory.create_dependency(
        "one",
        {
            "git": "https://github.com/demo/subdirectories.git",
            "subdirectory": "one",
            "platform": "linux",
        },
    )
    dependency_one_copy = Factory.create_dependency(
        "one",
        {
            "git": "https://github.com/demo/subdirectories.git",
            "subdirectory": "one-copy",
            "platform": "win32",
        },
    )

    root.add_dependency(dependency_one)
    root.add_dependency(dependency_one_copy)

    cache = DependencyCache(provider)
    cache.search_for.cache_clear()

    # ensure cache was never hit for both calls
    cache.search_for(dependency_one)
    cache.search_for(dependency_one_copy)
    assert not cache.search_for.cache_info().hits

    # increase test coverage by searching for copies
    # (when searching for the exact same object, __eq__ is never called)
    packages_one = cache.search_for(deepcopy(dependency_one))
    packages_one_copy = cache.search_for(deepcopy(dependency_one_copy))

    assert cache.search_for.cache_info().hits == 2
    assert cache.search_for.cache_info().currsize == 2

    assert len(packages_one) == len(packages_one_copy) == 1

    package_one = packages_one[0]
    package_one_copy = packages_one_copy[0]

    assert package_one.package.name == package_one_copy.package.name
    assert package_one.package.version.text == package_one_copy.package.version.text
    assert (
        package_one.package.source_type == package_one_copy.package.source_type == "git"
    )
    assert (
        package_one.package.source_resolved_reference
        == package_one_copy.package.source_resolved_reference
        == MOCK_DEFAULT_GIT_REVISION
    )
    assert (
        package_one.package.source_subdirectory
        != package_one_copy.package.source_subdirectory
    )
    assert package_one.package.source_subdirectory == "one"
    assert package_one_copy.package.source_subdirectory == "one-copy"

    assert package_one.dependency.marker.intersect(
        package_one_copy.dependency.marker
    ).is_empty()
