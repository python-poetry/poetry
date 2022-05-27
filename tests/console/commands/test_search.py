from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    import httpretty

    from cleo.testers.command_tester import CommandTester

    from tests.types import CommandTesterFactory

TESTS_DIRECTORY = Path(__file__).parent.parent.parent
FIXTURES_DIRECTORY = (
    TESTS_DIRECTORY / "repositories" / "fixtures" / "pypi.org" / "search"
)


@pytest.fixture(autouse=True)
def mock_search_http_response(http: type[httpretty.httpretty]) -> None:
    with FIXTURES_DIRECTORY.joinpath("search.html").open(encoding="utf-8") as f:
        http.register_uri("GET", "https://pypi.org/search", f.read())


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("search")


def test_search(tester: CommandTester, http: type[httpretty.httpretty]):
    tester.execute("sqlalchemy")

    expected = """
sqlalchemy (1.3.10)
 Database Abstraction Library

sqlalchemy-dao (1.3.1)
 Simple wrapper for sqlalchemy.

graphene-sqlalchemy (2.2.2)
 Graphene SQLAlchemy integration

sqlalchemy-utcdatetime (1.0.4)
 Convert to/from timezone aware datetimes when storing in a DBMS

paginate-sqlalchemy (0.3.0)
 Extension to paginate.Page that supports SQLAlchemy queries

sqlalchemy-audit (0.1.0)
 sqlalchemy-audit provides an easy way to set up revision tracking for your data.

transmogrify-sqlalchemy (1.0.2)
 Feed data from SQLAlchemy into a transmogrifier pipeline

sqlalchemy-schemadisplay (1.3)
 Turn SQLAlchemy DB Model into a graph

sqlalchemy-traversal (0.5.2)
 UNKNOWN

sqlalchemy-filters (0.10.0)
 A library to filter SQLAlchemy queries.

sqlalchemy-wrap (2.1.7)
 Python wrapper for the CircleCI API

sqlalchemy-nav (0.0.2)
 SQLAlchemy-Nav provides SQLAlchemy Mixins for creating navigation bars compatible with\
 Bootstrap

sqlalchemy-repr (0.0.1)
 Automatically generates pretty repr of a SQLAlchemy model.

sqlalchemy-diff (0.1.3)
 Compare two database schemas using sqlalchemy.

sqlalchemy-equivalence (0.1.1)
 Provides natural equivalence support for SQLAlchemy declarative models.

broadway-sqlalchemy (0.0.1)
 A broadway extension wrapping Flask-SQLAlchemy

jsonql-sqlalchemy (1.0.1)
 Simple JSON-Based CRUD Query Language for SQLAlchemy

sqlalchemy-plus (0.2.0)
 Create Views and Materialized Views with SqlAlchemy

cherrypy-sqlalchemy (0.5.3)
 Use SQLAlchemy with CherryPy

sqlalchemy-sqlany (1.0.3)
 SAP Sybase SQL Anywhere dialect for SQLAlchemy
"""

    output = tester.io.fetch_output()

    assert output == expected
