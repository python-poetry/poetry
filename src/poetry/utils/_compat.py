from __future__ import annotations

import locale
import sys
import warnings

from contextlib import suppress


if sys.version_info < (3, 11):
    # compatibility for python <3.11
    import tomli as tomllib
else:
    import tomllib

from importlib import metadata as _metadata


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


def __getattr__(name: str) -> object:
    if name == "metadata":
        warnings.warn(
            "Importing `metadata` from `poetry.utils._compat` is deprecated;"
            " use `importlib.metadata` directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _metadata
    raise AttributeError


__all__ = [
    "WINDOWS",
    "decode",
    "encode",
    "getencoding",
    "tomllib",
]
