import pytest
import tempfile

import tomlkit

from poetry.packages.locker import Locker
from poetry.packages.project_package import ProjectPackage

from ..helpers import get_package


@pytest.fixture
def locker():
    with tempfile.NamedTemporaryFile() as f:
        f.close()
        locker = Locker(f.name, {})

        return locker


@pytest.fixture
def root():
    return ProjectPackage("root", "1.2.3")


def test_lock_file_data_is_ordered(locker, root):
    package_a = get_package("A", "1.0.0")
    package_a.add_dependency("B", "^1.0")
    package_a.hashes = ["456", "123"]
    packages = [package_a, get_package("B", "1.2")]

    locker.set_lock_data(root, packages)

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    expected = """[[package]]
category = "main"
description = ""
name = "A"
optional = false
python-versions = "*"
version = "1.0.0"

[package.dependencies]
B = "^1.0"

[[package]]
category = "main"
description = ""
name = "B"
optional = false
python-versions = "*"
version = "1.2"

[metadata]
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
python-versions = "*"

[metadata.hashes]
A = ["123", "456"]
B = []
"""

    assert expected == content


def test_locker_properly_loads_extras(locker):
    content = """\
[[package]]
category = "main"
description = "httplib2 caching for requests"
name = "cachecontrol"
optional = false
python-versions = ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*"
version = "0.12.5"

[package.dependencies]
msgpack = "*"
requests = "*"

[package.dependencies.lockfile]
optional = true
version = ">=0.9"

[package.extras]
filecache = ["lockfile (>=0.9)"]
redis = ["redis (>=2.10.5)"]

[metadata]
content-hash = "c3d07fca33fba542ef2b2a4d75bf5b48d892d21a830e2ad9c952ba5123a52f77"
python-versions = "~2.7 || ^3.4"

[metadata.hashes]
cachecontrol = []
"""

    locker.lock.write(tomlkit.parse(content))

    packages = locker.locked_repository().packages

    assert 1 == len(packages)

    package = packages[0]
    assert 3 == len(package.requires)
    assert 2 == len(package.extras)

    lockfile_dep = package.extras["filecache"][0]
    assert lockfile_dep.name == "lockfile"
