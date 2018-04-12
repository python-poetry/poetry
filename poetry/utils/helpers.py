import re
import shutil
import tempfile

from contextlib import contextmanager

_canonicalize_regex = re.compile('[-_.]+')


def canonicalize_name(name):  # type: (str) -> str
    return _canonicalize_regex.sub('-', name).lower()


def module_name(name):  # type: (str) -> str
    return canonicalize_name(name).replace('-', '_')


@contextmanager
def temporary_directory(*args, **kwargs):
    try:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory(*args, **kwargs) as name:
            yield name
    except ImportError:
        name = tempfile.mkdtemp(*args, **kwargs)

        yield name

        shutil.rmtree(name)
