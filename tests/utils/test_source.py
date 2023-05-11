from __future__ import annotations

import pytest

from tomlkit.container import Container
from tomlkit.items import Table
from tomlkit.items import Trivia

from poetry.config.source import Source
from poetry.repositories.repository_pool import Priority
from poetry.utils.source import source_to_table


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

    assert source_to_table(source) == table


def test_source_default_is_primary() -> None:
    source = Source("foo", "https://example.com")
    assert source.priority == Priority.PRIMARY


@pytest.mark.parametrize(
    ("default", "secondary", "expected_priority"),
    [
        (False, True, Priority.SECONDARY),
        (True, False, Priority.DEFAULT),
        (True, True, Priority.DEFAULT),
    ],
)
def test_source_legacy_handling(
    default: bool, secondary: bool, expected_priority: Priority
) -> None:
    with pytest.warns(DeprecationWarning):
        source = Source(
            "foo", "https://example.com", default=default, secondary=secondary
        )
    assert source.priority == expected_priority


@pytest.mark.parametrize(
    ("priority", "expected_priority"),
    [
        ("secondary", Priority.SECONDARY),
        ("SECONDARY", Priority.SECONDARY),
    ],
)
def test_source_priority_as_string(priority: str, expected_priority: Priority) -> None:
    source = Source(
        "foo",
        "https://example.com",
        priority=priority,  # type: ignore[arg-type]
    )
    assert source.priority == Priority.SECONDARY
