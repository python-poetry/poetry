from __future__ import annotations

import locale
import sys
import warnings

from contextlib import suppress
from pathlib import Path


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


def is_relative_to(path1: Path, path2: Path) -> bool:
    """
    Checks if path1 is relative to path2.

    Works also if one of both paths has a Windows long path prefix.
    A long path prefix may be added when calling Path.resolve().
    """
    if WINDOWS:
        # Work around an issue that is_relative_to() does not work if
        # one of both paths has a long path prefix and the other path has not.
        long_path_prefix = "\\\\?\\"
        long_path_unc_prefix = f"{long_path_prefix}UNC\\"

        def remove_long_path_prefix(path: Path) -> Path:
            if (path_str := str(path)).startswith(long_path_prefix):
                if path_str.startswith(long_path_unc_prefix):
                    path = Path("\\\\" + path_str.removeprefix(long_path_unc_prefix))
                else:
                    path = Path(path_str.removeprefix(long_path_prefix))
            return path

        path1 = remove_long_path_prefix(path1)
        path2 = remove_long_path_prefix(path2)

    return path1.is_relative_to(path2)


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
