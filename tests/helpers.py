from poetry.packages import Dependency
from poetry.packages import Package

from poetry.utils._compat import Path

from functools import wraps
import tomlkit


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
    err = ValueError("{path}: {a} != {b}".format(path=path, a=a, b=b))

    def make_path(entry):
        return _path + (str(entry),)

    if isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b):
            raise err

        for idx, vals in enumerate(zip(a, b)):
            p = make_path(idx)
            if ".".join(p) not in ignore_paths:
                assert_deepequals(*vals, _path=p, ignore_paths=ignore_paths)

    elif isinstance(a, dict):
        if not isinstance(b, dict):
            raise err

        for key in set(list(a.keys()) + list(b.keys())):
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
