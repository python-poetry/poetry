from __future__ import annotations

import re

from typing import TYPE_CHECKING

import pytest

from poetry.repositories.pypi_repository import PyPiRepository


if TYPE_CHECKING:
    import httpretty

    from cleo.testers.command_tester import CommandTester

    from poetry.poetry import Poetry
    from poetry.repositories.legacy_repository import LegacyRepository
    from tests.types import CommandTesterFactory


SQLALCHEMY_SEARCH_OUTPUT_PYPI = """\
 Package                  Version Source Description
 broadway-sqlalchemy      0.0.1   PyPI   A broadway extension wrapping Flask-SQLAlchemy
 cherrypy-sqlalchemy      0.5.3   PyPI   Use SQLAlchemy with CherryPy
 graphene-sqlalchemy      2.2.2   PyPI   Graphene SQLAlchemy integration
 jsonql-sqlalchemy        1.0.1   PyPI   Simple JSON-Based CRUD Query Language for SQLAlchemy
 paginate-sqlalchemy      0.3.0   PyPI   Extension to paginate.Page that supports SQLAlchemy queries
 sqlalchemy               1.3.10  PyPI   Database Abstraction Library
 sqlalchemy-audit         0.1.0   PyPI   sqlalchemy-audit provides an easy way to set up revision tracking for your data.
 sqlalchemy-dao           1.3.1   PyPI   Simple wrapper for sqlalchemy.
 sqlalchemy-diff          0.1.3   PyPI   Compare two database schemas using sqlalchemy.
 sqlalchemy-equivalence   0.1.1   PyPI   Provides natural equivalence support for SQLAlchemy declarative models.
 sqlalchemy-filters       0.10.0  PyPI   A library to filter SQLAlchemy queries.
 sqlalchemy-nav           0.0.2   PyPI   SQLAlchemy-Nav provides SQLAlchemy Mixins for creating navigation bars compatible with Bootstrap
 sqlalchemy-plus          0.2.0   PyPI   Create Views and Materialized Views with SqlAlchemy
 sqlalchemy-repr          0.0.1   PyPI   Automatically generates pretty repr of a SQLAlchemy model.
 sqlalchemy-schemadisplay 1.3     PyPI   Turn SQLAlchemy DB Model into a graph
 sqlalchemy-sqlany        1.0.3   PyPI   SAP Sybase SQL Anywhere dialect for SQLAlchemy
 sqlalchemy-traversal     0.5.2   PyPI   UNKNOWN
 sqlalchemy-utcdatetime   1.0.4   PyPI   Convert to/from timezone aware datetimes when storing in a DBMS
 sqlalchemy-wrap          2.1.7   PyPI   Python wrapper for the CircleCI API
 transmogrify-sqlalchemy  1.0.2   PyPI   Feed data from SQLAlchemy into a transmogrifier pipeline
"""


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("search")


def clean_output(text: str) -> str:
    return re.sub(r"\s+\n", "\n", text)


def test_search(
    tester: CommandTester, http: type[httpretty.httpretty], poetry: Poetry
) -> None:
    # we expect PyPI in the default behaviour
    poetry.pool.add_repository(PyPiRepository())

    tester.execute("sqlalchemy")

    output = clean_output(tester.io.fetch_output())

    assert output == SQLALCHEMY_SEARCH_OUTPUT_PYPI


def test_search_empty_results(
    tester: CommandTester,
    http: type[httpretty.httpretty],
    poetry: Poetry,
    legacy_repository: LegacyRepository,
) -> None:
    poetry.pool.add_repository(legacy_repository)

    tester.execute("does-not-exist")

    output = tester.io.fetch_output()
    assert output.strip() == "No matching packages were found."


def test_search_with_legacy_repository(
    tester: CommandTester,
    http: type[httpretty.httpretty],
    poetry: Poetry,
    legacy_repository: LegacyRepository,
) -> None:
    poetry.pool.add_repository(PyPiRepository())
    poetry.pool.add_repository(legacy_repository)

    tester.execute("sqlalchemy")

    line_before = " sqlalchemy-filters       0.10.0  PyPI   A library to filter SQLAlchemy queries."
    additional_line = " sqlalchemy-legacy        4.3.4   legacy"
    expected = SQLALCHEMY_SEARCH_OUTPUT_PYPI.replace(
        line_before, f"{line_before}\n{additional_line}"
    )

    output = clean_output(tester.io.fetch_output())

    assert output == expected


def test_search_only_legacy_repository(
    tester: CommandTester,
    http: type[httpretty.httpretty],
    poetry: Poetry,
    legacy_repository: LegacyRepository,
) -> None:
    poetry.pool.add_repository(legacy_repository)

    tester.execute("ipython")

    expected = """\
 Package Version Source Description
 ipython 5.7.0   legacy
 ipython 7.5.0   legacy
"""

    output = clean_output(tester.io.fetch_output())
    assert output == expected


def test_search_multiple_queries(
    tester: CommandTester,
    http: type[httpretty.httpretty],
    poetry: Poetry,
    legacy_repository: LegacyRepository,
) -> None:
    poetry.pool.add_repository(legacy_repository)

    tester.execute("ipython isort")

    expected = """\
 Package        Version Source Description
 ipython        5.7.0   legacy
 ipython        7.5.0   legacy
 isort          4.3.4   legacy
 isort-metadata 4.3.4   legacy
"""

    output = clean_output(tester.io.fetch_output())

    # we use a set here to avoid ordering issues
    assert set(output.split("\n")) == set(expected.split("\n"))
