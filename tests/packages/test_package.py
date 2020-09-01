# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from poetry.packages import Package


def test_package_authors():
    package = Package("foo", "0.1.0")

    package.authors.append("Sébastien Eustace <sebastien@eustace.io>")
    assert package.author_name == "Sébastien Eustace"
    assert package.author_email == "sebastien@eustace.io"

    package.authors.insert(
        0, "Raphaël Yancey <raphael@badfile.net>"
    )  # With combining diacritics (ë = e + ¨ = e\u0308)
    assert package.author_name == "Raphaël Yancey"  # Is normalized into \u00EB
    assert package.author_email == "raphael@badfile.net"

    package.authors.insert(
        0, "Raphaël Yancey <raphael@badfile.net>"
    )  # Without (ë = \u00EB)
    assert package.author_name == "Raphaël Yancey"
    assert package.author_email == "raphael@badfile.net"

    package.authors.insert(0, "John Doe")
    assert package.author_name == "John Doe"
    assert package.author_email is None


def test_package_authors_invalid():
    package = Package("foo", "0.1.0")

    package.authors.insert(0, "<John Doe")
    with pytest.raises(ValueError) as e:
        package.author_name

    assert (
        str(e.value)
        == "Invalid author string. Must be in the format: John Smith <john@example.com>"
    )


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


@pytest.mark.parametrize("category", ["main", "dev"])
@pytest.mark.parametrize("optional", [True, False])
def test_package_url_category_optional(category, optional):
    package = Package("foo", "0.1.0")

    dependency = package.add_dependency(
        "poetry",
        constraint={
            "url": "https://github.com/python-poetry/poetry/releases/download/1.0.5/poetry-1.0.5-linux.tar.gz",
            "optional": optional,
        },
        category=category,
    )
    assert dependency.category == category
    assert dependency.is_optional() == optional
