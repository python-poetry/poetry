from __future__ import annotations

import locale
import sys

from contextlib import suppress
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


if sys.version_info < (3, 11):
    # compatibility for python <3.11
    import tomli as tomllib
else:
    import tomllib


if sys.version_info < (3, 10):
    # compatibility for python <3.10
    import importlib_metadata as metadata
else:
    from importlib import metadata

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


def getencoding() -> str:
    if sys.version_info < (3, 11):
        return locale.getpreferredencoding()
    else:
        return locale.getencoding()


def is_relative_to(this: Path, other: Path) -> bool:
    """
    Return whether `this` path is relative to the `other` path. This is compatibility wrapper around
    `PurePath.is_relative_to()` method. This method was introduced only in Python 3.9.

    See: https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.is_relative_to
    """
    if sys.version_info < (3, 9):
        with suppress(ValueError):
            this.relative_to(other)
            return True
        return False

    return this.is_relative_to(other)


__all__ = [
    "WINDOWS",
    "decode",
    "encode",
    "getencoding",
    "is_relative_to",
    "metadata",
    "tomllib",
]
