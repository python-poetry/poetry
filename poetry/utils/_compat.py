import sys


try:
    from importlib import metadata
except ImportError:
    # compatibility for python <3.8
    import importlib_metadata as metadata  # noqa

WINDOWS = sys.platform == "win32"


def decode(string, encodings=None):
    if not isinstance(string, bytes):
        return string

    encodings = encodings or ["utf-8", "latin1", "ascii"]

    for encoding in encodings:
        try:
            return string.decode(encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    return string.decode(encodings[0], errors="ignore")


def encode(string, encodings=None):
    if isinstance(string, bytes):
        return string

    encodings = encodings or ["utf-8", "latin1", "ascii"]

    for encoding in encodings:
        try:
            return string.encode(encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    return string.encode(encodings[0], errors="ignore")


def to_str(string):
    return decode(string)


def list_to_shell_command(cmd):
    return " ".join(
        f'"{token}"' if " " in token and token[0] not in {"'", '"'} else token
        for token in cmd
    )
