from __future__ import annotations

import warnings


from poetry.repositories.cached_repository import (  # isort: skip # nopycln: import # noqa: E501, F401
    CachedRepository,
)

warnings.warn(
    "Module poetry.repositories.cached is renamed and scheduled for removal in poetry"
    " release 1.4.0. Please migrate to poetry.repositories.cached_repository.",
    DeprecationWarning,
    stacklevel=2,
)
