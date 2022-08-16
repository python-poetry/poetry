import tempfile

import pytest
import tomlkit

from poetry.core.packages.project_package import ProjectPackage
from poetry.packages.locker import Locker

from ..helpers import get_dependency
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
    package_a.files = [{"file": "foo", "hash": "456"}, {"file": "bar", "hash": "123"}]
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

[metadata.files]
A = [
    {file = "bar", hash = "123"},
    {file = "foo", hash = "456"},
]
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

[metadata.files]
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

[metadata.files]
A = []
"""

    assert expected == content


def test_lock_file_should_not_have_mixed_types(locker, root):
    package_a = get_package("A", "1.0.0")
    package_a.add_dependency("B", "^1.0.0")
    package_a.add_dependency("B", {"version": ">=1.0.0", "optional": True})
    package_a.requires[-1].activate()
    package_a.extras["foo"] = [get_dependency("B", ">=1.0.0")]

    locker.set_lock_data(root, [package_a])

    expected = """[[package]]
category = "main"
description = ""
name = "A"
optional = false
python-versions = "*"
version = "1.0.0"

[package.dependencies]
[[package.dependencies.B]]
version = "^1.0.0"

[[package.dependencies.B]]
optional = true
version = ">=1.0.0"

[package.extras]
foo = ["B (>=1.0.0)"]

[metadata]
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
python-versions = "*"

[metadata.files]
A = []
"""

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    assert expected == content


def test_reading_lock_file_should_raise_an_error_on_invalid_data(locker):
    content = """[[package]]
category = "main"
description = ""
name = "A"
optional = false
python-versions = "*"
version = "1.0.0"

[package.extras]
foo = ["bar"]

[package.extras]
foo = ["bar"]

[metadata]
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
python-versions = "*"

[metadata.files]
A = []
"""
    with locker.lock.open("w", encoding="utf-8") as f:
        f.write(content)

    with pytest.raises(RuntimeError) as e:
        _ = locker.lock_data

    assert "Unable to read the lock file" in str(e.value)


def test_locking_legacy_repository_package_should_include_source_section(root, locker):
    package_a = get_package("A", "1.0.0")
    package_a.source_url = "https://foo.bar"
    package_a.source_reference = "legacy"
    packages = [package_a]

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

[package.source]
reference = "legacy"
url = "https://foo.bar"

[metadata]
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
python-versions = "*"

[metadata.files]
A = []
"""

    assert expected == content


def test_extras_dependencies_are_ordered(locker, root):
    package_a = get_package("A", "1.0.0")
    package_a.add_dependency(
        "B", {"version": "^1.0.0", "optional": True, "extras": ["c", "a", "b"]}
    )
    package_a.requires[-1].activate()

    locker.set_lock_data(root, [package_a])

    expected = """[[package]]
category = "main"
description = ""
name = "A"
optional = false
python-versions = "*"
version = "1.0.0"

[package.dependencies]
B = {version = "^1.0.0", extras = ["a", "b", "c"], optional = true}

[metadata]
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
python-versions = "*"

[metadata.files]
A = []
"""

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    assert expected == content
