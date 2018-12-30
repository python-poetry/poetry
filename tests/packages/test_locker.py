import pytest
import tempfile

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


def test_lock_packages_with_null_description(locker, root):
    package_a = get_package("A", "1.0.0")
    package_a.description = None

    locker.set_lock_data(root, [package_a])

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    expected = """[[package]]
category = "main"
description = ""
name = "A"
optional = false
python-versions = "*"
version = "1.0.0"

[metadata]
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
python-versions = "*"

[metadata.hashes]
A = []
"""

    assert expected == content
