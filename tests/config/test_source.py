from __future__ import annotations

import pytest

from tomlkit.container import Container
from tomlkit.items import Table
from tomlkit.items import Trivia

from poetry.config.source import Source
from poetry.repositories.repository_pool import Priority


@pytest.mark.parametrize(
    "source,table_body",
    [
        (
            Source("foo", "https://example.com"),
            {
                "name": "foo",
                "priority": "primary",
                "url": "https://example.com",
            },
        ),
        (
            Source("bar", "https://example.com/bar", priority=Priority.EXPLICIT),
            {
                "name": "bar",
                "priority": "explicit",
                "url": "https://example.com/bar",
            },
        ),
    ],
)
def test_source_to_table(source: Source, table_body: dict[str, str | bool]) -> None:
    table = Table(Container(), Trivia(), False)
    table._value = table_body  # type: ignore[assignment]

    assert source.to_toml_table() == table


def test_source_default_is_primary() -> None:
    source = Source("foo", "https://example.com")
    assert source.priority == Priority.PRIMARY


@pytest.mark.parametrize(
    ("priority", "expected_priority"),
    [
        ("supplemental", Priority.SUPPLEMENTAL),
        ("SUPPLEMENTAL", Priority.SUPPLEMENTAL),
    ],
)
def test_source_priority_as_string(priority: str, expected_priority: Priority) -> None:
    source = Source(
        "foo",
        "https://example.com",
        priority=priority,  # type: ignore[arg-type]
    )
    assert source.priority == Priority.SUPPLEMENTAL
