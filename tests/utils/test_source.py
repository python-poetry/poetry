from __future__ import annotations

import pytest

from tomlkit.container import Container
from tomlkit.items import Table
from tomlkit.items import Trivia

from poetry.config.source import Source
from poetry.utils.source import source_to_table


@pytest.mark.parametrize(
    "source,table_body",
    [
        (
            Source("foo", "https://example.com"),
            {
                "default": False,
                "name": "foo",
                "secondary": False,
                "url": "https://example.com",
            },
        ),
        (
            Source("bar", "https://example.com/bar", True, True),
            {
                "default": True,
                "name": "bar",
                "secondary": True,
                "url": "https://example.com/bar",
            },
        ),
    ],
)
def test_source_to_table(source: Source, table_body: dict[str, str | bool]):
    table = Table(Container(), Trivia(), False)
    table._value = table_body

    assert source_to_table(source) == table
