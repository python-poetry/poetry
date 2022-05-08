from __future__ import annotations

from typing import Callable

from poetry.utils._compat import metadata


# The metadata.version that we import for Python 3.7 is untyped, work around
# that.
version: Callable[[str], str] = metadata.version

__version__ = version("poetry")
