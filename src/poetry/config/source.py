import dataclasses

from typing import Dict
from typing import Union


@dataclasses.dataclass(order=True, eq=True)
class Source:
    name: str
    url: str
    default: bool = dataclasses.field(default=False)
    secondary: bool = dataclasses.field(default=False)

    def to_dict(self) -> Dict[str, Union[str, bool]]:
        return dataclasses.asdict(self)
