from __future__ import annotations


try:
    import zipp  # nopycln: import
except ImportError:
    import zipfile as zipp  # noqa: F401, TC002

try:
    from typing import Protocol  # nopycln: import
except ImportError:
    from typing_extensions import Protocol  # noqa: F401, TC002
