from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester

    from poetry.config.source import Source
    from poetry.poetry import Poetry
    from tests.types import CommandTesterFactory
    from tests.types import ProjectFactory


@pytest.fixture
def tester(
    command_tester_factory: CommandTesterFactory,
    poetry_with_source: Poetry,
    add_multiple_sources: None,
) -> CommandTester:
    return command_tester_factory("source remove", poetry=poetry_with_source)


@pytest.fixture
def tester_pypi(
    command_tester_factory: CommandTesterFactory,
    poetry_with_pypi: Poetry,
) -> CommandTester:
    return command_tester_factory("source remove", poetry=poetry_with_pypi)


@pytest.fixture
def tester_pypi_and_other(
    command_tester_factory: CommandTesterFactory,
    poetry_with_pypi_and_other: Poetry,
) -> CommandTester:
    return command_tester_factory("source remove", poetry=poetry_with_pypi_and_other)


@pytest.mark.parametrize("modifier", ["lower", "upper"])
def test_source_remove_simple(
    tester: CommandTester,
    poetry_with_source: Poetry,
    source_existing: Source,
    source_one: Source,
    source_two: Source,
    modifier: str,
) -> None:
    tester.execute(getattr(f"{source_existing.name}", modifier)())
    assert (
        tester.io.fetch_output().strip()
        == f"Removing source with name {source_existing.name}."
    )

    poetry_with_source.pyproject.reload()
    sources = poetry_with_source.get_sources()
    assert sources == [source_one, source_two]

    assert tester.status_code == 0


@pytest.mark.parametrize("name", ["pypi", "PyPI"])
def test_source_remove_pypi(
    name: str, tester_pypi: CommandTester, poetry_with_pypi: Poetry
) -> None:
    tester_pypi.execute(name)
    assert tester_pypi.io.fetch_output().strip() == "Removing source with name PyPI."

    poetry_with_pypi.pyproject.reload()
    sources = poetry_with_pypi.get_sources()
    assert sources == []

    assert tester_pypi.status_code == 0


@pytest.mark.parametrize("name", ["pypi", "PyPI"])
def test_source_remove_pypi_and_other(
    name: str,
    tester_pypi_and_other: CommandTester,
    poetry_with_pypi_and_other: Poetry,
    source_existing: Source,
) -> None:
    tester_pypi_and_other.execute(name)
    assert (
        tester_pypi_and_other.io.fetch_output().strip()
        == "Removing source with name PyPI."
    )

    poetry_with_pypi_and_other.pyproject.reload()
    sources = poetry_with_pypi_and_other.get_sources()
    assert sources == [source_existing]

    assert tester_pypi_and_other.status_code == 0


@pytest.mark.parametrize("name", ["foo", "pypi", "PyPI"])
def test_source_remove_error(name: str, tester: CommandTester) -> None:
    tester.execute(name)
    assert tester.io.fetch_error().strip() == f"Source with name {name} was not found."
    assert tester.status_code == 1


PYPROJECT_WITH_REFERENCED_SOURCE = """
[tool.poetry]
name = "source-command-test"
version = "0.1.0"
description = ""
authors = ["Poetry Tester <tester@poetry.org>"]

[tool.poetry.dependencies]
python = "^3.9"

{tables}
[[tool.poetry.source]]
name = "existing"
url = "https://existing.com"
"""

REFERENCE_TABLES = {
    "main": 'mylib = {version = "^1.0", source = "existing"}',
    "main-list": (
        "mylib = [\n"
        '    {version = "^1.0", source = "existing", python = ">=3.11"},\n'
        '    {version = "^0.9", source = "existing", python = "<3.11"},\n'
        "]"
    ),
    "group": (
        "[tool.poetry.group.dev.dependencies]\n"
        'mylib = {version = "^1.0", source = "existing"}'
    ),
}


@pytest.fixture
def poetry_with_referenced_source(
    project_factory: ProjectFactory, request: pytest.FixtureRequest
) -> Poetry:
    tables = REFERENCE_TABLES[request.param]
    return project_factory(
        pyproject_content=PYPROJECT_WITH_REFERENCED_SOURCE.format(tables=tables)
    )


@pytest.mark.parametrize(
    "poetry_with_referenced_source",
    ["main", "main-list", "group"],
    indirect=True,
)
@pytest.mark.parametrize("name", ["existing", "EXISTING"])
def test_source_remove_referenced_by_dependency(
    poetry_with_referenced_source: Poetry,
    command_tester_factory: CommandTesterFactory,
    source_existing: Source,
    name: str,
) -> None:
    tester = command_tester_factory(
        "source remove", poetry=poetry_with_referenced_source
    )

    tester.execute(name)

    error = tester.io.fetch_error()
    assert tester.status_code == 1
    assert f'Cannot remove source "{name}"' in error
    assert "mylib" in error

    poetry_with_referenced_source.pyproject.reload()
    assert poetry_with_referenced_source.get_sources() == [source_existing]


def test_source_remove_unreferenced_source_kept_working(
    project_factory: ProjectFactory,
    command_tester_factory: CommandTesterFactory,
    source_existing: Source,
) -> None:
    poetry = project_factory(
        pyproject_content=PYPROJECT_WITH_REFERENCED_SOURCE.format(
            tables='mylib = {version = "^1.0", source = "other"}'
        )
    )
    tester = command_tester_factory("source remove", poetry=poetry)

    tester.execute("existing")

    assert tester.status_code == 0
    poetry.pyproject.reload()
    assert poetry.get_sources() == []
