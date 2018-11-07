import os
import tarfile
import zipfile

from contextlib import contextmanager

from poetry.masonry import api
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
