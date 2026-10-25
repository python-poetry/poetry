from __future__ import annotations

from poetry.core.exceptions import PoetryCoreError
from tomlrt import TOMLError as _TOMLRtError


class TOMLError(_TOMLRtError, PoetryCoreError):
    pass
