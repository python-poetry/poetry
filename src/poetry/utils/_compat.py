from __future__ import annotations

import sys

from contextlib import suppress
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from importlib import metadata

    import importlib_metadata as metadata
    import tomli as tomllib
    import tomllib


# TODO: use try/except ImportError when
# https://github.com/python/mypy/issues/1393 is fixed

if sys.version_info < (3, 11):
    # compatibility for python <3.11
    pass
else:
    pass  # nopycln: import


if sys.version_info < (3, 10):
    # compatibility for python <3.10
    pass
else:
    pass

WINDOWS = sys.platform == "win32"


def decode(string: bytes | str, encodings: list[str] | None = None) -> str:
    if not isinstance(string, bytes):
        return string

    encodings = encodings or ["utf-8", "latin1", "ascii"]

    for encoding in encodings:
        with suppress(UnicodeEncodeError, UnicodeDecodeError):
            return string.decode(encoding)

    return string.decode(encodings[0], errors="ignore")


def encode(string: str, encodings: list[str] | None = None) -> bytes:
    if isinstance(string, bytes):
        return string

    encodings = encodings or ["utf-8", "latin1", "ascii"]

    for encoding in encodings:
        with suppress(UnicodeEncodeError, UnicodeDecodeError):
            return string.encode(encoding)

    return string.encode(encodings[0], errors="ignore")


__all__ = [
    "WINDOWS",
    "decode",
    "encode",
    "metadata",
    "tomllib",
]
