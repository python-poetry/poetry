from __future__ import annotations

import dataclasses


@dataclasses.dataclass(order=True, eq=True)
class Source:
    name: str
    url: str
    default: bool = dataclasses.field(default=False)
    secondary: bool = dataclasses.field(default=False)

    def to_dict(self) -> dict[str, str | bool]:
        return dataclasses.asdict(self)
