import sys

try:
    import pathlib2
    from pathlib2 import Path
except ImportError:
    from pathlib import Path

try:  # Python 2
    long = long
    unicode = unicode
    basestring = basestring
except NameError:  # Python 3
    long = int
    unicode = str
    basestring = str


PY2 = sys.version_info[0] == 2
PY35 = sys.version_info >= (3, 5)
PY36 = sys.version_info >= (3, 6)


def decode(string, encodings=None):
    if not PY2 and not isinstance(string, bytes):
        return string

    if PY2 and isinstance(string, unicode):
        return string

    encodings = encodings or ["utf-8", "latin1", "ascii"]

    for encoding in encodings:
        try:
            return string.decode(encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    return string.decode(encodings[0], errors="ignore")


def encode(string, encodings=None):
    if not PY2 and isinstance(string, bytes):
        return string

    if PY2 and isinstance(string, str):
        return string

    encodings = encodings or ["utf-8", "latin1", "ascii"]

    for encoding in encodings:
        try:
            return string.encode(encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    return string.encode(encodings[0], errors="ignore")


def to_str(string):
    if isinstance(string, str) or not isinstance(string, (unicode, bytes)):
        return string

    if PY2:
        method = "encode"
    else:
        method = "decode"

    encodings = ["utf-8", "latin1", "ascii"]

    for encoding in encodings:
        try:
            return getattr(string, method)(encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    return getattr(string, method)(encodings[0], errors="ignore")
