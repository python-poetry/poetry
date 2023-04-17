from __future__ import annotations

import sys


if sys.version_info < (3, 8):
    import zipp as zipfile  # nopycln: import

    from typing_extensions import Protocol  # nopycln: import
else:
    import zipfile

    from typing import Protocol

__all__ = ["zipfile", "Protocol"]
