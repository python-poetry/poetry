# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import tarfile
import zipfile

from contextlib import contextmanager

from poetry import __version__
from poetry.masonry import api
from poetry.utils._compat import Path
from poetry.utils._compat import decode
from poetry.utils.helpers import temporary_directory


@contextmanager
def cwd(directory):
    prev = os.getcwd()
    os.chdir(str(directory))
    try:
        yield
    finally:
        os.chdir(prev)


fixtures = os.path.join(os.path.dirname(__file__), "builders", "fixtures")


def test_get_requires_for_build_wheel():
    expected = ["cleo>=0.6.0,<0.7.0", "cachy[msgpack]>=0.2.0,<0.3.0"]
    with cwd(os.path.join(fixtures, "complete")):
        api.get_requires_for_build_wheel() == expected


def test_get_requires_for_build_sdist():
    expected = ["cleo>=0.6.0,<0.7.0", "cachy[msgpack]>=0.2.0,<0.3.0"]
    with cwd(os.path.join(fixtures, "complete")):
        api.get_requires_for_build_sdist() == expected


def test_build_wheel():
    with temporary_directory() as tmp_dir, cwd(os.path.join(fixtures, "complete")):
        filename = api.build_wheel(tmp_dir)

        with zipfile.ZipFile(str(os.path.join(tmp_dir, filename))) as zip:
            namelist = zip.namelist()

            assert "my_package-1.2.3.dist-info/entry_points.txt" in namelist
            assert "my_package-1.2.3.dist-info/WHEEL" in namelist
            assert "my_package-1.2.3.dist-info/METADATA" in namelist


def test_build_sdist():
    with temporary_directory() as tmp_dir, cwd(os.path.join(fixtures, "complete")):
        filename = api.build_sdist(tmp_dir)

        with tarfile.open(str(os.path.join(tmp_dir, filename))) as tar:
            namelist = tar.getnames()

            assert "my-package-1.2.3/LICENSE" in namelist


def test_prepare_metadata_for_build_wheel():
    entry_points = """\
[console_scripts]
extra-script=my_package.extra:main[time]
my-2nd-script=my_package:main2
my-script=my_package:main

"""
    wheel_data = """\
Wheel-Version: 1.0
Generator: poetry {}
Root-Is-Purelib: true
Tag: py3-none-any
""".format(
        __version__
    )
    metadata = """\
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
Project-URL: Documentation, https://poetry.eustace.io/docs
Project-URL: Repository, https://github.com/sdispater/poetry
Description-Content-Type: text/x-rst

My Package
==========

"""
    with temporary_directory() as tmp_dir, cwd(os.path.join(fixtures, "complete")):
        dirname = api.prepare_metadata_for_build_wheel(tmp_dir)

        assert "my_package-1.2.3.dist-info" == dirname

        dist_info = Path(tmp_dir, dirname)

        assert (dist_info / "entry_points.txt").exists()
        assert (dist_info / "WHEEL").exists()
        assert (dist_info / "METADATA").exists()

        with (dist_info / "entry_points.txt").open(encoding="utf-8") as f:
            assert entry_points == decode(f.read())

        with (dist_info / "WHEEL").open(encoding="utf-8") as f:
            assert wheel_data == decode(f.read())

        with (dist_info / "METADATA").open(encoding="utf-8") as f:
            assert metadata == decode(f.read())
