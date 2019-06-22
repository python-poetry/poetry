import os
import shutil

from functools import wraps

import tomlkit

from poetry.packages import Dependency
from poetry.packages import Package
from poetry.utils._compat import PY2
from poetry.utils._compat import WINDOWS
from poetry.utils._compat import Path
from poetry.utils._compat import urlparse
from poetry.vcs.git import ParsedUrl


FIXTURE_PATH = Path(__file__).parent / "fixtures"


def get_package(name, version):
    return Package(name, version)


def get_dependency(
    name, constraint=None, category="main", optional=False, allows_prereleases=False
):
    return Dependency(
        name,
        constraint or "*",
        category=category,
        optional=optional,
        allows_prereleases=allows_prereleases,
    )


def fixture(path=None):
    if path:
        return FIXTURE_PATH / path
    else:
        return FIXTURE_PATH


def copy_or_symlink(source, dest):
    if dest.exists():
        if dest.is_symlink():
            os.unlink(str(dest))
        elif dest.is_dir():
            shutil.rmtree(str(dest))
        else:
            os.unlink(str(dest))

    # Python2 does not support os.symlink on Windows whereas Python3 does.
    # os.symlink requires either administrative privileges or developer mode on Win10,
    # throwing an OSError if neither is active.
    if WINDOWS:
        if PY2:
            if source.is_dir():
                shutil.copytree(str(source), str(dest))
            else:
                shutil.copyfile(str(source), str(dest))
        else:
            try:
                os.symlink(str(source), str(dest), target_is_directory=source.is_dir())
            except OSError:
                if source.is_dir():
                    shutil.copytree(str(source), str(dest))
                else:
                    shutil.copyfile(str(source), str(dest))
    else:
        os.symlink(str(source), str(dest))


def mock_clone(_, source, dest):
    # Checking source to determine which folder we need to copy
    parsed = ParsedUrl.parse(source)

    folder = (
        Path(__file__).parent
        / "fixtures"
        / "git"
        / parsed.resource
        / parsed.pathname.lstrip("/").rstrip(".git")
    )

    copy_or_symlink(folder, dest)


def mock_download(self, url, dest):
    parts = urlparse.urlparse(url)

    fixtures = Path(__file__).parent / "fixtures"
    fixture = fixtures / parts.path.lstrip("/")

    copy_or_symlink(fixture, dest)


def assert_deepequals(a, b, ignore_paths=None, _path=None):
    """Compare objects a and b keeping track of object path for error reporting.

    Keyword arguments:
    a -- Object a
    b -- Object b
    ignore_paths -- List of object paths (delimited by .)

    Example:
    assert_deepequals({
        "poetry-version": "1.0.0a3",
        "content-hash": "example",
    }, {
      "metadata": {
        "poetry-version": "1.0.0a4",
        "content-hash": "example",
      }
    }, ignore_paths=set(["metadata.poetry-version"]))
    """

    _path = _path if _path else tuple()
    ignore_paths = ignore_paths if ignore_paths else set()
    path = ".".join(_path)
    err = ValueError("{}: {} != {}".format(path, a, b))

    def make_path(entry):
        return _path + (str(entry),)

    if isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b):
            raise err

        for vals in zip(a, b):
            p = make_path("[]")
            if ".".join(p) not in ignore_paths:
                assert_deepequals(*vals, _path=p, ignore_paths=ignore_paths)

    elif isinstance(a, dict):
        if not isinstance(b, dict):
            raise err

        for key in set(a.keys()) | set(b.keys()):
            p = make_path(key)
            if ".".join(p) not in ignore_paths:
                assert_deepequals(a[key], b[key], _path=p, ignore_paths=ignore_paths)

    elif a == b:
        return

    else:
        raise err


@wraps(assert_deepequals)
def assert_deepequals_toml(a, b, **kwargs):
    a = dict(tomlkit.parse(a))
    b = dict(tomlkit.parse(b))
    return assert_deepequals(a, b, **kwargs)
