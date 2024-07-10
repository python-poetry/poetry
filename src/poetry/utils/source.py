from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from tomlkit.items import Table

    from poetry.config.source import Source


def source_to_table(source: Source) -> Table:
    from tomlkit import nl
    from tomlkit import table

    source_table: Table = table()
    for key, value in source.to_dict().items():
        source_table.add(key, value)
    source_table.add(nl())
    return source_table
