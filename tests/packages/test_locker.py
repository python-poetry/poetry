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
platform = "*"
python-versions = "*"
version = "1.0.0"

[package.dependencies]
B = "^1.0"

[[package]]
category = "main"
description = ""
name = "B"
optional = false
platform = "*"
python-versions = "*"
version = "1.2"

[metadata]
content-hash = "78ac9903d6fcbe1b1322857731bff3cac904ef8fd5e72c6c768761f28f66b8ea"
platform = "*"
python-versions = "*"

[metadata.hashes]
A = ["123", "456"]
B = []
"""

    assert expected == content
