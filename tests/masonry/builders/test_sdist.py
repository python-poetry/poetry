# -*- coding: utf-8 -*-
import ast
import pytest
import re
import shutil
import tarfile

from email.parser import Parser

from poetry.io import NullIO
from poetry.masonry.builders.sdist import SdistBuilder
from poetry.masonry.utils.package_include import PackageInclude
from poetry.packages import Package
from poetry.poetry import Poetry
from poetry.utils._compat import Path
from poetry.utils._compat import to_str
from poetry.utils.venv import NullVenv

from tests.helpers import get_dependency


fixtures_dir = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def setup():
    clear_samples_dist()

    yield

    clear_samples_dist()


def clear_samples_dist():
    for dist in fixtures_dir.glob("**/dist"):
        if dist.is_dir():
            shutil.rmtree(str(dist))


def project(name):
    return Path(__file__).parent / "fixtures" / name


def test_convert_dependencies():
    package = Package("foo", "1.2.3")
    result = SdistBuilder.convert_dependencies(
        package,
        [
            get_dependency("A", "^1.0"),
            get_dependency("B", "~1.0"),
            get_dependency("C", "1.2.3"),
        ],
    )
    main = ["A>=1.0,<2.0", "B>=1.0,<1.1", "C==1.2.3"]
    extras = {}

    assert result == (main, extras)

    package = Package("foo", "1.2.3")
    package.extras = {"bar": [get_dependency("A")]}

    result = SdistBuilder.convert_dependencies(
        package,
        [
            get_dependency("A", ">=1.2", optional=True),
            get_dependency("B", "~1.0"),
            get_dependency("C", "1.2.3"),
        ],
    )
    main = ["B>=1.0,<1.1", "C==1.2.3"]
    extras = {"bar": ["A>=1.2"]}

    assert result == (main, extras)

    c = get_dependency("C", "1.2.3")
    c.python_versions = "~2.7 || ^3.6"
    d = get_dependency("D", "3.4.5", optional=True)
    d.python_versions = "~2.7 || ^3.4"

    package.extras = {"baz": [get_dependency("D")]}

    result = SdistBuilder.convert_dependencies(
        package,
        [
            get_dependency("A", ">=1.2", optional=True),
            get_dependency("B", "~1.0"),
            c,
            d,
        ],
    )
    main = ["B>=1.0,<1.1"]

    extra_python = (
        ':(python_version >= "2.7" and python_version < "2.8") '
        'or (python_version >= "3.6" and python_version < "4.0")'
    )
    extra_d_dependency = (
        'baz:(python_version >= "2.7" and python_version < "2.8") '
        'or (python_version >= "3.4" and python_version < "4.0")'
    )
    extras = {extra_python: ["C==1.2.3"], extra_d_dependency: ["D==3.4.5"]}

    assert result == (main, extras)


def test_make_setup():
    poetry = Poetry.create(project("complete"))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())
    setup = builder.build_setup()
    setup_ast = ast.parse(setup)

    setup_ast.body = [n for n in setup_ast.body if isinstance(n, ast.Assign)]
    ns = {}
    exec(compile(setup_ast, filename="setup.py", mode="exec"), ns)
    assert ns["packages"] == [
        "my_package",
        "my_package.sub_pkg1",
        "my_package.sub_pkg2",
    ]
    assert ns["install_requires"] == ["cachy[msgpack]>=0.2.0,<0.3.0", "cleo>=0.6,<0.7"]
    assert ns["entry_points"] == {
        "console_scripts": [
            "my-2nd-script = my_package:main2",
            "my-script = my_package:main",
        ]
    }
    assert ns["extras_require"] == {"time": ["pendulum>=1.4,<2.0"]}


def test_make_pkg_info():
    poetry = Poetry.create(project("complete"))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())
    pkg_info = builder.build_pkg_info()
    p = Parser()
    parsed = p.parsestr(to_str(pkg_info))

    assert parsed["Metadata-Version"] == "2.1"
    assert parsed["Name"] == "my-package"
    assert parsed["Version"] == "1.2.3"
    assert parsed["Summary"] == "Some description."
    assert parsed["Author"] == "Sébastien Eustace"
    assert parsed["Author-email"] == "sebastien@eustace.io"
    assert parsed["Keywords"] == "packaging,dependency,poetry"
    assert parsed["Requires-Python"] == ">=3.6,<4.0"

    classifiers = parsed.get_all("Classifier")
    assert classifiers == [
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]

    extras = parsed.get_all("Provides-Extra")
    assert extras == ["time"]

    requires = parsed.get_all("Requires-Dist")
    assert requires == [
        "cachy[msgpack] (>=0.2.0,<0.3.0)",
        "cleo (>=0.6,<0.7)",
        'pendulum (>=1.4,<2.0); extra == "time"',
    ]


def test_make_pkg_info_any_python():
    poetry = Poetry.create(project("module1"))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())
    pkg_info = builder.build_pkg_info()
    p = Parser()
    parsed = p.parsestr(to_str(pkg_info))

    assert "Requires-Python" not in parsed


def test_find_files_to_add():
    poetry = Poetry.create(project("complete"))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())
    result = builder.find_files_to_add()

    assert sorted(result) == sorted(
        [
            Path("LICENSE"),
            Path("README.rst"),
            Path("my_package/__init__.py"),
            Path("my_package/data1/test.json"),
            Path("my_package/sub_pkg1/__init__.py"),
            Path("my_package/sub_pkg2/__init__.py"),
            Path("my_package/sub_pkg2/data2/data.json"),
            Path("pyproject.toml"),
        ]
    )


def test_find_packages():
    poetry = Poetry.create(project("complete"))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())

    base = project("complete")
    include = PackageInclude(base, "my_package")

    pkg_dir, packages, pkg_data = builder.find_packages(include)

    assert pkg_dir is None
    assert packages == ["my_package", "my_package.sub_pkg1", "my_package.sub_pkg2"]
    assert pkg_data == {
        "": ["*"],
        "my_package": ["data1/*"],
        "my_package.sub_pkg2": ["data2/*"],
    }

    poetry = Poetry.create(project("source_package"))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())

    base = project("source_package")
    include = PackageInclude(base, "package_src", "src")

    pkg_dir, packages, pkg_data = builder.find_packages(include)

    assert pkg_dir == str(base / "src")
    assert packages == ["package_src"]
    assert pkg_data == {"": ["*"]}


def test_package():
    poetry = Poetry.create(project("complete"))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())
    builder.build()

    sdist = fixtures_dir / "complete" / "dist" / "my-package-1.2.3.tar.gz"

    assert sdist.exists()

    tar = tarfile.open(str(sdist), "r")

    assert "my-package-1.2.3/LICENSE" in tar.getnames()


def test_module():
    poetry = Poetry.create(project("module1"))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())
    builder.build()

    sdist = fixtures_dir / "module1" / "dist" / "module1-0.1.tar.gz"

    assert sdist.exists()

    tar = tarfile.open(str(sdist), "r")

    assert "module1-0.1/module1.py" in tar.getnames()


def test_prelease():
    poetry = Poetry.create(project("prerelease"))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())
    builder.build()

    sdist = fixtures_dir / "prerelease" / "dist" / "prerelease-0.1b1.tar.gz"

    assert sdist.exists()


def test_with_c_extensions():
    poetry = Poetry.create(project("extended"))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())
    builder.build()

    sdist = fixtures_dir / "extended" / "dist" / "extended-0.1.tar.gz"

    assert sdist.exists()

    tar = tarfile.open(str(sdist), "r")

    assert "extended-0.1/build.py" in tar.getnames()
    assert "extended-0.1/extended/extended.c" in tar.getnames()


def test_with_src_module_file():
    poetry = Poetry.create(project("source_file"))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())

    # Check setup.py
    setup = builder.build_setup()
    setup_ast = ast.parse(setup)

    setup_ast.body = [n for n in setup_ast.body if isinstance(n, ast.Assign)]
    ns = {}
    exec(compile(setup_ast, filename="setup.py", mode="exec"), ns)
    assert ns["package_dir"] == {"": "src"}
    assert ns["modules"] == ["module_src"]

    builder.build()

    sdist = fixtures_dir / "source_file" / "dist" / "module-src-0.1.tar.gz"

    assert sdist.exists()

    tar = tarfile.open(str(sdist), "r")

    assert "module-src-0.1/src/module_src.py" in tar.getnames()


def test_with_src_module_dir():
    poetry = Poetry.create(project("source_package"))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())

    # Check setup.py
    setup = builder.build_setup()
    setup_ast = ast.parse(setup)

    setup_ast.body = [n for n in setup_ast.body if isinstance(n, ast.Assign)]
    ns = {}
    exec(compile(setup_ast, filename="setup.py", mode="exec"), ns)
    assert ns["package_dir"] == {"": "src"}
    assert ns["packages"] == ["package_src"]

    builder.build()

    sdist = fixtures_dir / "source_package" / "dist" / "package-src-0.1.tar.gz"

    assert sdist.exists()

    tar = tarfile.open(str(sdist), "r")

    assert "package-src-0.1/src/package_src/__init__.py" in tar.getnames()
    assert "package-src-0.1/src/package_src/module.py" in tar.getnames()


def test_package_with_include(mocker):
    # Patch git module to return specific excluded files
    p = mocker.patch("poetry.vcs.git.Git.get_ignored_files")
    p.return_value = [
        str(
            Path(__file__).parent
            / "fixtures"
            / "with-include"
            / "extra_dir"
            / "vcs_excluded.txt"
        ),
        str(
            Path(__file__).parent
            / "fixtures"
            / "with-include"
            / "extra_dir"
            / "sub_pkg"
            / "vcs_excluded.txt"
        ),
    ]
    poetry = Poetry.create(project("with-include"))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())

    # Check setup.py
    setup = builder.build_setup()
    setup_ast = ast.parse(setup)

    setup_ast.body = [n for n in setup_ast.body if isinstance(n, ast.Assign)]
    ns = {}
    exec(compile(setup_ast, filename="setup.py", mode="exec"), ns)
    assert "package_dir" not in ns
    assert ns["packages"] == ["extra_dir", "extra_dir.sub_pkg", "package_with_include"]
    assert ns["modules"] == ["my_module"]

    builder.build()

    sdist = fixtures_dir / "with-include" / "dist" / "with-include-1.2.3.tar.gz"

    assert sdist.exists()

    tar = tarfile.open(str(sdist), "r")

    names = tar.getnames()
    assert "with-include-1.2.3/LICENSE" in names
    assert "with-include-1.2.3/README.rst" in names
    assert "with-include-1.2.3/extra_dir/__init__.py" in names
    assert "with-include-1.2.3/extra_dir/vcs_excluded.txt" in names
    assert "with-include-1.2.3/extra_dir/sub_pkg/__init__.py" in names
    assert "with-include-1.2.3/extra_dir/sub_pkg/vcs_excluded.txt" not in names
    assert "with-include-1.2.3/my_module.py" in names
    assert "with-include-1.2.3/notes.txt" in names
    assert "with-include-1.2.3/package_with_include/__init__.py" in names
    assert "with-include-1.2.3/pyproject.toml" in names
    assert "with-include-1.2.3/setup.py" in names
    assert "with-include-1.2.3/PKG-INFO" in names


def test_proper_python_requires_if_single_version_specified():
    poetry = Poetry.create(project("simple_version"))

    builder = SdistBuilder(poetry, NullVenv(), NullIO())
    pkg_info = builder.build_pkg_info()
    p = Parser()
    parsed = p.parsestr(to_str(pkg_info))

    assert parsed["Requires-Python"] == ">=3.6,<3.7"
