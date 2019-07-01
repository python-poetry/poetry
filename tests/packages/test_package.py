# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from poetry.packages import Package
from poetry.version.markers import EmptyMarker


def test_package_authors():
    package = Package("foo", "0.1.0")

    package.authors.append("Sébastien Eustace <sebastien@eustace.io>")
    assert package.author_name == "Sébastien Eustace"
    assert package.author_email == "sebastien@eustace.io"

    package.authors.insert(0, "John Doe")
    assert package.author_name == "John Doe"
    assert package.author_email is None


def test_package_empty_marker():
    package = Package("foo", "0.1.0")
    package.marker = EmptyMarker()

    dep = package.to_dependency()
    assert dep.python_versions == "*"
