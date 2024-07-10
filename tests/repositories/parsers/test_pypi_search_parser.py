from __future__ import annotations

from pathlib import Path

import pytest

from poetry.repositories.parsers.pypi_search_parser import Result
from poetry.repositories.parsers.pypi_search_parser import SearchResultParser


FIXTURES_DIRECTORY = Path(__file__).parent.parent / "fixtures" / "pypi.org" / "search"


@pytest.fixture
def search_page_data() -> str:
    with FIXTURES_DIRECTORY.joinpath("search.html").open(encoding="utf-8") as f:
        return f.read()


def test_search_parser(search_page_data: str) -> None:
    parser = SearchResultParser()
    parser.feed(search_page_data)
    assert parser.results == [
        Result(
            name="SQLAlchemy",
            version="1.3.10",
            description="Database Abstraction Library",
        ),
        Result(
            name="SQLAlchemy-Dao",
            version="1.3.1",
            description="Simple wrapper for sqlalchemy.",
        ),
        Result(
            name="graphene-sqlalchemy",
            version="2.2.2",
            description="Graphene SQLAlchemy integration",
        ),
        Result(
            name="SQLAlchemy-UTCDateTime",
            version="1.0.4",
            description=(
                "Convert to/from timezone aware datetimes when storing in a DBMS"
            ),
        ),
        Result(
            name="paginate_sqlalchemy",
            version="0.3.0",
            description="Extension to paginate.Page that supports SQLAlchemy queries",
        ),
        Result(
            name="sqlalchemy_audit",
            version="0.1.0",
            description=(
                "sqlalchemy-audit provides an easy way to set up revision "
                "tracking for your data."
            ),
        ),
        Result(
            name="transmogrify.sqlalchemy",
            version="1.0.2",
            description="Feed data from SQLAlchemy into a transmogrifier pipeline",
        ),
        Result(
            name="sqlalchemy_schemadisplay",
            version="1.3",
            description="Turn SQLAlchemy DB Model into a graph",
        ),
        Result(name="sqlalchemy_traversal", version="0.5.2", description="UNKNOWN"),
        Result(
            name="sqlalchemy-filters",
            version="0.10.0",
            description="A library to filter SQLAlchemy queries.",
        ),
        Result(
            name="SQLAlchemy-wrap",
            version="2.1.7",
            description="Python wrapper for the CircleCI API",
        ),
        Result(
            name="sqlalchemy-nav",
            version="0.0.2",
            description=(
                "SQLAlchemy-Nav provides SQLAlchemy Mixins for creating "
                "navigation bars compatible with Bootstrap"
            ),
        ),
        Result(
            name="sqlalchemy-repr",
            version="0.0.1",
            description="Automatically generates pretty repr of a SQLAlchemy model.",
        ),
        Result(
            name="sqlalchemy-diff",
            version="0.1.3",
            description="Compare two database schemas using sqlalchemy.",
        ),
        Result(
            name="SQLAlchemy-Equivalence",
            version="0.1.1",
            description=(
                "Provides natural equivalence support for SQLAlchemy "
                "declarative models."
            ),
        ),
        Result(
            name="Broadway-SQLAlchemy",
            version="0.0.1",
            description="A broadway extension wrapping Flask-SQLAlchemy",
        ),
        Result(
            name="jsonql-sqlalchemy",
            version="1.0.1",
            description="Simple JSON-Based CRUD Query Language for SQLAlchemy",
        ),
        Result(
            name="sqlalchemy-plus",
            version="0.2.0",
            description="Create Views and Materialized Views with SqlAlchemy",
        ),
        Result(
            name="CherryPy-SQLAlchemy",
            version="0.5.3",
            description="Use SQLAlchemy with CherryPy",
        ),
        Result(
            name="sqlalchemy_sqlany",
            version="1.0.3",
            description="SAP Sybase SQL Anywhere dialect for SQLAlchemy",
        ),
    ]
