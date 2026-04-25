from __future__ import annotations

import dataclasses

from typing import TYPE_CHECKING

from poetry.repositories.repository_pool import Priority


if TYPE_CHECKING:
    from tomlrt import Table


@dataclasses.dataclass(order=True, eq=True)
class Source:
    name: str
    url: str = ""
    priority: Priority = (
        Priority.PRIMARY
    )  # cheating in annotation: str will be converted to Priority in __post_init__

    def __post_init__(self) -> None:
        if isinstance(self.priority, str):
            self.priority = Priority[self.priority.upper()]

    def to_dict(self) -> dict[str, str | bool]:
        return dataclasses.asdict(
            self,
            dict_factory=lambda x: {
                k: v if not isinstance(v, Priority) else v.name.lower()
                for (k, v) in x
                if v
            },
        )

    def to_toml_table(self) -> Table:
        from tomlrt import Table

        return Table.section(self.to_dict())
