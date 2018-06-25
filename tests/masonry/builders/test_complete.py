# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest
import re
import shutil
import tarfile
import zipfile

from poetry import __version__
from poetry.io import NullIO
from poetry.masonry.builders import CompleteBuilder
from poetry.poetry import Poetry
from poetry.utils._compat import Path
from poetry.utils._compat import decode
from poetry.utils.venv import NullVenv

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


@pytest.mark.skipif(sys.platform == "win32" and sys.version_info <= (3, 4))
def test_wheel_c_extension():
    module_path = fixtures_dir / "extended"
    builder = CompleteBuilder(Poetry.create(module_path), NullVenv(True), NullIO())
    builder.build()

    sdist = fixtures_dir / "extended" / "dist" / "extended-0.1.tar.gz"

    assert sdist.exists()

    tar = tarfile.open(str(sdist), "r")

    assert "extended-0.1/build.py" in tar.getnames()
    assert "extended-0.1/extended/extended.c" in tar.getnames()

    whl = list((module_path / "dist").glob("extended-0.1-cp*-cp*-*.whl"))[0]

    assert whl.exists()

    zip = zipfile.ZipFile(str(whl))

    has_compiled_extension = False
    for name in zip.namelist():
        if name.startswith("extended/extended") and name.endswith((".so", ".pyd")):
            has_compiled_extension = True

    assert has_compiled_extension

    try:
        wheel_data = decode(zip.read("extended-0.1.dist-info/WHEEL"))

        assert (
            re.match(
                """(?m)^\
Wheel-Version: 1.0
Generator: poetry {}
Root-Is-Purelib: false
Tag: cp[23]\d-cp[23]\dmu?-.+
$""".format(
                    __version__
                ),
                wheel_data,
            )
            is not None
        )
    finally:
        zip.close()


def test_complete():
    module_path = fixtures_dir / "complete"
    builder = CompleteBuilder(Poetry.create(module_path), NullVenv(True), NullIO())
    builder.build()

    whl = module_path / "dist" / "my_package-1.2.3-py3-none-any.whl"

    assert whl.exists()

    zip = zipfile.ZipFile(str(whl))

    try:
        entry_points = zip.read("my_package-1.2.3.dist-info/entry_points.txt")

        assert (
            decode(entry_points.decode())
            == """\
[console_scripts]
my-2nd-script=my_package:main2
my-script=my_package:main

"""
        )
        wheel_data = decode(zip.read("my_package-1.2.3.dist-info/WHEEL"))

        assert (
            wheel_data
            == """\
Wheel-Version: 1.0
Generator: poetry {}
Root-Is-Purelib: true
Tag: py3-none-any
""".format(
                __version__
            )
        )
        wheel_data = decode(zip.read("my_package-1.2.3.dist-info/METADATA"))

        assert (
            wheel_data
            == """\
Metadata-Version: 2.1
Name: my-package
Version: 1.2.3
Summary: Some description.
Home-page: https://poetry.eustace.io/
License: MIT
Keywords: packaging,dependency,poetry
Author: Sébastien Eustace
Author-email: sebastien@eustace.io
Requires-Python: >=3.6,<4.0
Classifier: License :: OSI Approved :: MIT License
Classifier: Programming Language :: Python :: 3
Classifier: Programming Language :: Python :: 3.6
Classifier: Programming Language :: Python :: 3.7
Classifier: Topic :: Software Development :: Build Tools
Classifier: Topic :: Software Development :: Libraries :: Python Modules
Provides-Extra: time
Requires-Dist: cachy[msgpack] (>=0.2.0,<0.3.0)
Requires-Dist: cleo (>=0.6,<0.7)
Requires-Dist: pendulum (>=1.4,<2.0); extra == "time"
Description-Content-Type: text/x-rst

My Package
==========

"""
        )
    finally:
        zip.close()


def test_module_src():
    module_path = fixtures_dir / "source_file"
    builder = CompleteBuilder(Poetry.create(module_path), NullVenv(True), NullIO())
    builder.build()

    sdist = module_path / "dist" / "module-src-0.1.tar.gz"

    assert sdist.exists()

    tar = tarfile.open(str(sdist), "r")

    assert "module-src-0.1/src/module_src.py" in tar.getnames()

    whl = module_path / "dist" / "module_src-0.1-py2.py3-none-any.whl"

    assert whl.exists()

    zip = zipfile.ZipFile(str(whl))

    try:
        assert "module_src.py" in zip.namelist()
    finally:
        zip.close()


def test_package_src():
    module_path = fixtures_dir / "source_package"
    builder = CompleteBuilder(Poetry.create(module_path), NullVenv(True), NullIO())
    builder.build()

    sdist = module_path / "dist" / "package-src-0.1.tar.gz"

    assert sdist.exists()

    tar = tarfile.open(str(sdist), "r")

    assert "package-src-0.1/src/package_src/module.py" in tar.getnames()

    whl = module_path / "dist" / "package_src-0.1-py2.py3-none-any.whl"

    assert whl.exists()

    zip = zipfile.ZipFile(str(whl))

    try:
        assert "package_src/__init__.py" in zip.namelist()
        assert "package_src/module.py" in zip.namelist()
    finally:
        zip.close()
