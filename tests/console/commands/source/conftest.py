from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.config.source import Source
from poetry.repositories.repository_pool import Priority


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
def source_default_deprecated() -> Source:
    return Source(name="default", url="https://default.com", default=True)


@pytest.fixture
def source_secondary_deprecated() -> Source:
    return Source(name="secondary", url="https://secondary.com", secondary=True)


@pytest.fixture
def source_primary() -> Source:
    return Source(name="primary", url="https://primary.com", priority=Priority.PRIMARY)


@pytest.fixture
def source_default() -> Source:
    return Source(name="default", url="https://default.com", priority=Priority.DEFAULT)


@pytest.fixture
def source_secondary() -> Source:
    return Source(
        name="secondary", url="https://secondary.com", priority=Priority.SECONDARY
    )


@pytest.fixture
def source_supplemental() -> Source:
    return Source(
        name="supplemental",
        url="https://supplemental.com",
        priority=Priority.SUPPLEMENTAL,
    )


@pytest.fixture
def source_explicit() -> Source:
    return Source(
        name="explicit", url="https://explicit.com", priority=Priority.EXPLICIT
    )


@pytest.fixture
def source_pypi() -> Source:
    return Source(name="PyPI")


@pytest.fixture
def source_pypi_explicit() -> Source:
    return Source(name="PyPI", priority=Priority.EXPLICIT)


_existing_source = Source(name="existing", url="https://existing.com")


@pytest.fixture
def source_existing() -> Source:
    return _existing_source


PYPROJECT_WITHOUT_SOURCES = """
[tool.poetry]
name = "source-command-test"
version = "0.1.0"
description = ""
authors = ["Poetry Tester <tester@poetry.org>"]

[tool.poetry.dependencies]
python = "^3.9"

[tool.poetry.dev-dependencies]
"""


PYPROJECT_WITH_SOURCES = f"""{PYPROJECT_WITHOUT_SOURCES}

[[tool.poetry.source]]
name = "{_existing_source.name}"
url = "{_existing_source.url}"
"""


PYPROJECT_WITH_PYPI = f"""{PYPROJECT_WITHOUT_SOURCES}

[[tool.poetry.source]]
name = "PyPI"
"""


PYPROJECT_WITH_PYPI_AND_OTHER = f"""{PYPROJECT_WITH_SOURCES}

[[tool.poetry.source]]
name = "PyPI"
"""


@pytest.fixture
def poetry_without_source(project_factory: ProjectFactory) -> Poetry:
    return project_factory(pyproject_content=PYPROJECT_WITHOUT_SOURCES)


@pytest.fixture
def poetry_with_source(project_factory: ProjectFactory) -> Poetry:
    return project_factory(pyproject_content=PYPROJECT_WITH_SOURCES)


@pytest.fixture
def poetry_with_pypi(project_factory: ProjectFactory) -> Poetry:
    return project_factory(pyproject_content=PYPROJECT_WITH_PYPI)


@pytest.fixture
def poetry_with_pypi_and_other(project_factory: ProjectFactory) -> Poetry:
    return project_factory(pyproject_content=PYPROJECT_WITH_PYPI_AND_OTHER)


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


@pytest.fixture
def add_all_source_types(
    command_tester_factory: CommandTesterFactory,
    poetry_with_source: Poetry,
    source_primary: Source,
    source_default: Source,
    source_secondary: Source,
    source_supplemental: Source,
    source_explicit: Source,
) -> None:
    add = command_tester_factory("source add", poetry=poetry_with_source)
    for source in [
        source_primary,
        source_default,
        source_secondary,
        source_supplemental,
        source_explicit,
    ]:
        add.execute(f"{source.name} {source.url} --priority={source.name}")
