from typing import Dict  # noqa: TC002
from typing import Union  # noqa: TC002

import dataclasses


@dataclasses.dataclass(order=True, eq=True)
class Source:
    name: str
    url: str
    default: bool = dataclasses.field(default=False)
    secondary: bool = dataclasses.field(default=False)

    def to_dict(self) -> Dict[str, Union[str, bool]]:
        return dataclasses.asdict(self)
