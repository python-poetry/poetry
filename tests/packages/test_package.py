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
