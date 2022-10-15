from __future__ import annotations

import warnings


from poetry.repositories.http_repository import (  # isort: skip # nopycln: import # noqa: E501, F401
    HTTPRepository,
)

warnings.warn(
    "Module poetry.repositories.http is renamed and scheduled for removal in poetry"
    " release 1.4.0. Please migrate to poetry.repositories.http_repository.",
    DeprecationWarning,
    stacklevel=2,
)
