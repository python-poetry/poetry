# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from poetry.packages import Package


AUTHORS = (
    "Sébastien Eustace <sebastien@eustace.io>",
    "Sébastien Eustace<sebastien@eustace.io>",
    "Sébastien Eustace sebastien@eustace.io",
)


@pytest.mark.parametrize("author", AUTHORS)
def test_package_authors(author):
    package = Package("foo", "0.1.0")

    package.authors.append(author)
    assert package.author_name == "Sébastien Eustace"
    assert package.author_email == "sebastien@eustace.io"


def test_author_partial():
    """
    Checks Package for correct handling of partial authors
    (email only, for example)
    """
    package = Package("foo", "0.1.0")
    package.authors.append("support@example.com")
    assert package.author_name is None
    assert package.author_email == "support@example.com"

    package.authors[0] = "<support@example.com>"
    assert package.author_name is None
    assert package.author_email == "support@example.com"

    package.authors[0] = "John Doe"
    assert package.author_name == "John Doe"
    assert package.author_email is None
