from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.factory import Factory
from poetry.mixology.version_solver import DependencyCache
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

    packages_pypi = cache.search_for(dependency_pypi)
    packages_git = cache.search_for(dependency_git)

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
    assert (
        package_git.package.source_resolved_reference
        == "9cf87a285a2d3fbb0b9fa621997b3acc3631ed24"
    )
