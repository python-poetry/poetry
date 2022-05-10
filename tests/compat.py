from __future__ import annotations


try:
    import zipp
except ImportError:
    import zipfile as zipp  # noqa: F401, TC002

try:
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol  # noqa: F401, TC002

from poetry.core.semver.helpers import parse_constraint
from poetry.core.semver.version import Version

from poetry.utils._compat import metadata


is_poetry_core_1_1_0a7_compat = not parse_constraint(">1.1.0a7").allows(
    Version.parse(metadata.version("poetry-core"))
)
