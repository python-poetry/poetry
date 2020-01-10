import pytest

from poetry.masonry.utils.package_include import PackageInclude
from poetry.utils._compat import Path


fixtures_dir = Path(__file__).parent / "fixtures"
with_includes = fixtures_dir / "with_includes"


def test_package_include_with_multiple_dirs():
    pkg_include = PackageInclude(base=fixtures_dir, include="with_includes")
    assert pkg_include.elements == [
        with_includes / "__init__.py",
        with_includes / "bar",
        with_includes / "bar/baz.py",
        with_includes / "extra_package",
        with_includes / "extra_package/some_dir",
        with_includes / "extra_package/some_dir/foo.py",
        with_includes / "extra_package/some_dir/quux.py",
        with_includes / "not_a_python_pkg",
        with_includes / "not_a_python_pkg/baz.txt",
    ]


def test_package_include_with_simple_dir():
    pkg_include = PackageInclude(base=with_includes, include="bar")
    assert pkg_include.elements == [with_includes / "bar/baz.py"]


def test_package_include_with_nested_dir():
    pkg_include = PackageInclude(base=with_includes, include="extra_package/**/*.py")
    assert pkg_include.elements == [
        with_includes / "extra_package/some_dir/foo.py",
        with_includes / "extra_package/some_dir/quux.py",
    ]


def test_package_include_with_no_python_files_in_dir():
    with pytest.raises(ValueError) as e:
        PackageInclude(base=with_includes, include="not_a_python_pkg")

    assert str(e.value) == "not_a_python_pkg is not a package."
