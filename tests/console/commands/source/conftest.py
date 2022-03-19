from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.config.source import Source


if TYPE_CHECKING:
    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory
    from tests.types import ProjectFactory


@pytest.fixture
def source_one() -> Source:
    return Source(name="one", url="https://one.com")


@pytest.fixture
def source_two() -> Source:
    return Source(name="two", url="https://two.com")


@pytest.fixture
def source_default() -> Source:
    return Source(name="default", url="https://default.com", default=True)


@pytest.fixture
def source_secondary() -> Source:
    return Source(name="secondary", url="https://secondary.com", secondary=True)


_existing_source = Source(name="existing", url="https://existing.com")


@pytest.fixture
def source_existing() -> Source:
    return _existing_source


PYPROJECT_WITH_SOURCES = f"""
[tool.poetry]
name = "source-command-test"
version = "0.1.0"
description = ""
authors = ["Poetry Tester <tester@poetry.org>"]

[tool.poetry.dependencies]
python = "^3.9"

[tool.poetry.dev-dependencies]

[[tool.poetry.source]]
name = "{_existing_source.name}"
url = "{_existing_source.url}"
"""


@pytest.fixture
def poetry_with_source(project_factory: ProjectFactory) -> Poetry:
    return project_factory(pyproject_content=PYPROJECT_WITH_SOURCES)


@pytest.fixture
def add_multiple_sources(
    command_tester_factory: CommandTesterFactory,
    poetry_with_source: Poetry,
    source_one: Source,
    source_two: Source,
) -> None:
    add = command_tester_factory("source add", poetry=poetry_with_source)
    for source in [source_one, source_two]:
        add.execute(f"{source.name} {source.url}")
