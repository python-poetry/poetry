from __future__ import annotations

import sys


if sys.version_info < (3, 8):
    import zipp as zipfile  # nopycln: import
else:
    import zipfile  # noqa: F401

try:
    from typing import Protocol  # nopycln: import
except ImportError:
    from typing_extensions import Protocol  # noqa: F401, TC002
