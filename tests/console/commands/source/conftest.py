from typing import TYPE_CHECKING

import pytest

from poetry.config.source import Source


if TYPE_CHECKING:
    from poetry.config.config import Config
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


@pytest.fixture
def source_existing_global() -> Source:
    return Source(name="existing_global", url="https://existing_global.com")


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
def poetry_with_source(project_factory: "ProjectFactory") -> "Poetry":
    return project_factory(pyproject_content=PYPROJECT_WITH_SOURCES)


@pytest.fixture
def add_multiple_sources(
    command_tester_factory: "CommandTesterFactory",
    poetry_with_source: "Poetry",
    source_one: Source,
    source_two: Source,
) -> None:
    add = command_tester_factory("source add", poetry=poetry_with_source)
    for source in [source_one, source_two]:
        add.execute(f"{source.name} {source.url}")


@pytest.fixture
def config_with_source(config: "Config", source_existing_global: Source) -> "Config":
    config.merge(
        {
            "sources": {
                source_existing_global.name: {
                    "url": source_existing_global.url,
                    "default": source_existing_global.default,
                    "secondary": source_existing_global.secondary,
                }
            }
        }
    )
    return config
