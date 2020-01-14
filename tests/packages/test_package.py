# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from poetry.packages import Package
from poetry.packages import VCSDependency


def test_package_authors():
    package = Package("foo", "0.1.0")

    package.authors.append("Sébastien Eustace <sebastien@eustace.io>")
    assert package.author_name == "Sébastien Eustace"
    assert package.author_email == "sebastien@eustace.io"

    package.authors.insert(0, "John Doe")
    assert package.author_name == "John Doe"
    assert package.author_email is None


@pytest.mark.parametrize("category", ["main", "dev"])
def test_package_add_dependency_vcs_category(category):
    package = Package("foo", "0.1.0")

    dependency = package.add_dependency(
        "poetry",
        constraint={"git": "https://github.com/python-poetry/poetry.git"},
        category=category,
    )
    assert dependency.category == category


def test_package_add_dependency_vcs_category_default_main():
    package = Package("foo", "0.1.0")

    dependency = package.add_dependency(
        "poetry", constraint={"git": "https://github.com/python-poetry/poetry.git"}
    )
    assert dependency.category == "main"


def test_package_add_dependency_vcs__with_subdirectory():
    package = Package("foo", "0.1.0")

    dependency = package.add_dependency(
        "poetry",
        constraint={
            "git": "https://github.com/demo/project_in_subdirectory.git",
            "subdirectory": "mypackage",
        },
    )
    assert dependency.source == "https://github.com/demo/project_in_subdirectory.git"
    assert dependency.subdirectory == "mypackage"
    assert isinstance(dependency, VCSDependency)
