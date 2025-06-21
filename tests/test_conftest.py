from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from packaging.utils import canonicalize_name

from poetry.factory import Factory
from poetry.repositories import Repository


if TYPE_CHECKING:
    from tests.types import PackageFactory


@pytest.fixture
def repo() -> Repository:
    return Repository("repo")


def test_conftest_create_package(
    create_package: PackageFactory, repo: Repository
) -> None:
    dependency = Factory.create_dependency(
        "dependency", {"version": "*", "extras": ["download", "install"]}
    )
    package = create_package(
        "A",
        "1.0",
        dependencies=[dependency],
        extras={
            "download": ["download-package"],
            "install": ["install-package"],
            "py38": ["py38-package ; python_version == '3.8'"],
            "py310": ["py310-package ; python_version > '3.8'"],
            "all": ["a[download,install]"],
            "py": ["a[py38,py310]"],
            "nested": ["a[all]"],
        },
    )

    expected_extras = {"download", "install", "py38", "py310", "all", "py", "nested"}

    # test returned package instance
    assert package.name == "a"
    assert str(package.version) == "1.0"
    assert set(package.extras.keys()) == expected_extras

    # test package was correctly added to the repo
    assert repo.has_package(package)

    repo_package = repo.package(package.name, package.version)
    assert repo_package.name == "a"
    assert set(package.extras.keys()) == expected_extras

    assert repo.has_package(create_package("download-package", "1.0"))
    assert repo.has_package(create_package("install-package", "1.0"))
    assert repo.has_package(create_package("py38-package", "1.0"))
    assert repo.has_package(create_package("py310-package", "1.0"))

    # verify dependencies were correctly added
    requirements = {requirement.to_pep_508() for requirement in repo_package.requires}

    assert requirements == {
        dependency.to_pep_508(),
        'download-package (>=1.0,<2.0) ; extra == "download"',
        'install-package (>=1.0,<2.0) ; extra == "install"',
        'py310-package (>=1.0,<2.0) ; python_version > "3.8" and extra == "py310"',
        'py38-package (>=1.0,<2.0) ; python_version == "3.8" and extra == "py38"',
    }

    # verify self-referencing extras
    assert repo_package.extras[canonicalize_name("all")] == [
        Factory.create_dependency(
            "a", {"version": "*", "extras": ["download", "install"]}
        )
    ]
    assert repo_package.extras[canonicalize_name("nested")] == [
        Factory.create_dependency("a", {"version": "*", "extras": ["all"]})
    ]
