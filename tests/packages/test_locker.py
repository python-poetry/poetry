from __future__ import annotations

import json
import logging
import tempfile
import uuid

from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import tomlkit

from poetry.core.packages.package import Package
from poetry.core.packages.project_package import ProjectPackage
from poetry.core.semver.version import Version

from poetry.factory import Factory
from poetry.packages.locker import Locker
from tests.helpers import get_dependency
from tests.helpers import get_package


if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture
    from pytest_mock import MockerFixture


@pytest.fixture
def locker() -> Locker:
    with tempfile.NamedTemporaryFile() as f:
        f.close()
        locker = Locker(f.name, {})

        return locker


@pytest.fixture
def root() -> ProjectPackage:
    return ProjectPackage("root", "1.2.3")


def test_lock_file_data_is_ordered(locker: Locker, root: ProjectPackage):
    package_a = get_package("A", "1.0.0")
    package_a.add_dependency(Factory.create_dependency("B", "^1.0"))
    package_a.files = [{"file": "foo", "hash": "456"}, {"file": "bar", "hash": "123"}]
    package_a2 = get_package("A", "2.0.0")
    package_a2.files = [{"file": "baz", "hash": "345"}]
    package_git = Package(
        "git-package",
        "1.2.3",
        source_type="git",
        source_url="https://github.com/python-poetry/poetry.git",
        source_reference="develop",
        source_resolved_reference="123456",
    )
    package_url_linux = Package(
        "url-package",
        "1.0",
        source_type="url",
        source_url="https://example.org/url-package-1.0-cp39-manylinux_2_17_x86_64.whl",
    )
    package_url_win32 = Package(
        "url-package",
        "1.0",
        source_type="url",
        source_url="https://example.org/url-package-1.0-cp39-win_amd64.whl",
    )
    packages = [
        package_a2,
        package_a,
        get_package("B", "1.2"),
        package_git,
        package_url_win32,
        package_url_linux,
    ]

    locker.set_lock_data(root, packages)

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
[[package]]
name = "A"
version = "1.0.0"
description = ""
category = "main"
optional = false
python-versions = "*"

[package.dependencies]
B = "^1.0"

[[package]]
name = "A"
version = "2.0.0"
description = ""
category = "main"
optional = false
python-versions = "*"

[[package]]
name = "B"
version = "1.2"
description = ""
category = "main"
optional = false
python-versions = "*"

[[package]]
name = "git-package"
version = "1.2.3"
description = ""
category = "main"
optional = false
python-versions = "*"
develop = false

[package.source]
type = "git"
url = "https://github.com/python-poetry/poetry.git"
reference = "develop"
resolved_reference = "123456"

[[package]]
name = "url-package"
version = "1.0"
description = ""
category = "main"
optional = false
python-versions = "*"

[package.source]
type = "url"
url = "https://example.org/url-package-1.0-cp39-manylinux_2_17_x86_64.whl"

[[package]]
name = "url-package"
version = "1.0"
description = ""
category = "main"
optional = false
python-versions = "*"

[package.source]
type = "url"
url = "https://example.org/url-package-1.0-cp39-win_amd64.whl"

[metadata]
lock-version = "1.1"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"

[metadata.files]
A = [
    {file = "bar", hash = "123"},
    {file = "foo", hash = "456"},
    {file = "baz", hash = "345"},
]
B = []
git-package = []
url-package = []
"""

    assert content == expected


def test_locker_properly_loads_extras(locker: Locker):
    content = """\
[[package]]
name = "cachecontrol"
version = "0.12.5"
description = "httplib2 caching for requests"
category = "main"
optional = false
python-versions = ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*"

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
lock-version = "1.1"
python-versions = "~2.7 || ^3.4"
content-hash = "c3d07fca33fba542ef2b2a4d75bf5b48d892d21a830e2ad9c952ba5123a52f77"

[metadata.files]
cachecontrol = []
"""

    locker.lock.write(tomlkit.parse(content))

    packages = locker.locked_repository().packages

    assert len(packages) == 1

    package = packages[0]
    assert len(package.requires) == 3
    assert len(package.extras) == 2

    lockfile_dep = package.extras["filecache"][0]
    assert lockfile_dep.name == "lockfile"


def test_locker_properly_loads_nested_extras(locker: Locker):
    content = """\
[[package]]
name = "a"
version = "1.0"
description = ""
category = "main"
optional = false
python-versions = "*"

[package.dependencies]
b = {version = "^1.0", optional = true, extras = "c"}

[package.extras]
b = ["b[c] (>=1.0,<2.0)"]

[[package]]
name = "b"
version = "1.0"
description = ""
category = "main"
optional = false
python-versions = "*"

[package.dependencies]
c = {version = "^1.0", optional = true}

[package.extras]
c = ["c (>=1.0,<2.0)"]

[[package]]
name = "c"
version = "1.0"
description = ""
category = "main"
optional = false
python-versions = "*"

[metadata]
python-versions = "*"
lock-version = "1.1"
content-hash = "123456789"

[metadata.files]
"a" = []
"b" = []
"c" = []
"""

    locker.lock.write(tomlkit.parse(content))

    repository = locker.locked_repository()
    assert len(repository.packages) == 3

    packages = repository.find_packages(get_dependency("a", "1.0"))
    assert len(packages) == 1

    package = packages[0]
    assert len(package.requires) == 1
    assert len(package.extras) == 1

    dependency_b = package.extras["b"][0]
    assert dependency_b.name == "b"
    assert dependency_b.extras == frozenset({"c"})

    packages = repository.find_packages(dependency_b)
    assert len(packages) == 1

    package = packages[0]
    assert len(package.requires) == 1
    assert len(package.extras) == 1

    dependency_c = package.extras["c"][0]
    assert dependency_c.name == "c"
    assert dependency_c.extras == frozenset()

    packages = repository.find_packages(dependency_c)
    assert len(packages) == 1


def test_locker_properly_loads_extras_legacy(locker: Locker):
    content = """\
[[package]]
name = "a"
version = "1.0"
description = ""
category = "main"
optional = false
python-versions = "*"

[package.dependencies]
b = {version = "^1.0", optional = true}

[package.extras]
b = ["b (^1.0)"]

[[package]]
name = "b"
version = "1.0"
description = ""
category = "main"
optional = false
python-versions = "*"

[metadata]
python-versions = "*"
lock-version = "1.1"
content-hash = "123456789"

[metadata.files]
"a" = []
"b" = []
"""

    locker.lock.write(tomlkit.parse(content))

    repository = locker.locked_repository()
    assert len(repository.packages) == 2

    packages = repository.find_packages(get_dependency("a", "1.0"))
    assert len(packages) == 1

    package = packages[0]
    assert len(package.requires) == 1
    assert len(package.extras) == 1

    dependency_b = package.extras["b"][0]
    assert dependency_b.name == "b"


def test_lock_packages_with_null_description(locker: Locker, root: ProjectPackage):
    package_a = get_package("A", "1.0.0")
    package_a.description = None

    locker.set_lock_data(root, [package_a])

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    expected = """[[package]]
name = "A"
version = "1.0.0"
description = ""
category = "main"
optional = false
python-versions = "*"

[metadata]
lock-version = "1.1"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"

[metadata.files]
A = []
"""

    assert content == expected


def test_lock_file_should_not_have_mixed_types(locker: Locker, root: ProjectPackage):
    package_a = get_package("A", "1.0.0")
    package_a.add_dependency(Factory.create_dependency("B", "^1.0.0"))
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": ">=1.0.0", "optional": True})
    )
    package_a.requires[-1].activate()
    package_a.extras["foo"] = [get_dependency("B", ">=1.0.0")]

    locker.set_lock_data(root, [package_a])

    expected = """[[package]]
name = "A"
version = "1.0.0"
description = ""
category = "main"
optional = false
python-versions = "*"

[package.dependencies]
B = [
    {version = "^1.0.0"},
    {version = ">=1.0.0", optional = true},
]

[package.extras]
foo = ["B (>=1.0.0)"]

[metadata]
lock-version = "1.1"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"

[metadata.files]
A = []
"""

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    assert content == expected


def test_reading_lock_file_should_raise_an_error_on_invalid_data(locker: Locker):
    content = """[[package]]
name = "A"
version = "1.0.0"
description = ""
category = "main"
optional = false
python-versions = "*"

[package.extras]
foo = ["bar"]

[package.extras]
foo = ["bar"]

[metadata]
lock-version = "1.1"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"

[metadata.files]
A = []
"""
    with locker.lock.open("w", encoding="utf-8") as f:
        f.write(content)

    with pytest.raises(RuntimeError) as e:
        _ = locker.lock_data

    assert "Unable to read the lock file" in str(e.value)


def test_locking_legacy_repository_package_should_include_source_section(
    root: ProjectPackage, locker: Locker
):
    package_a = Package(
        "A",
        "1.0.0",
        source_type="legacy",
        source_url="https://foo.bar",
        source_reference="legacy",
    )
    packages = [package_a]

    locker.set_lock_data(root, packages)

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    expected = """[[package]]
name = "A"
version = "1.0.0"
description = ""
category = "main"
optional = false
python-versions = "*"

[package.source]
type = "legacy"
url = "https://foo.bar"
reference = "legacy"

[metadata]
lock-version = "1.1"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"

[metadata.files]
A = []
"""

    assert content == expected


def test_locker_should_emit_warnings_if_lock_version_is_newer_but_allowed(
    locker: Locker, caplog: LogCaptureFixture
):
    version = ".".join(Version.parse(Locker._VERSION).next_minor().text.split(".")[:2])
    content = f"""\
[metadata]
lock-version = "{version}"
python-versions = "~2.7 || ^3.4"
content-hash = "c3d07fca33fba542ef2b2a4d75bf5b48d892d21a830e2ad9c952ba5123a52f77"

[metadata.files]
"""
    caplog.set_level(logging.WARNING, logger="poetry.packages.locker")

    locker.lock.write(tomlkit.parse(content))

    _ = locker.lock_data

    assert len(caplog.records) == 1

    record = caplog.records[0]
    assert record.levelname == "WARNING"

    expected = """\
The lock file might not be compatible with the current version of Poetry.
Upgrade Poetry to ensure the lock file is read properly or, alternatively, \
regenerate the lock file with the `poetry lock` command.\
"""
    assert record.message == expected


def test_locker_should_raise_an_error_if_lock_version_is_newer_and_not_allowed(
    locker: Locker, caplog: LogCaptureFixture
):
    content = """\
[metadata]
lock-version = "2.0"
python-versions = "~2.7 || ^3.4"
content-hash = "c3d07fca33fba542ef2b2a4d75bf5b48d892d21a830e2ad9c952ba5123a52f77"

[metadata.files]
"""
    caplog.set_level(logging.WARNING, logger="poetry.packages.locker")

    locker.lock.write(tomlkit.parse(content))

    with pytest.raises(RuntimeError, match="^The lock file is not compatible"):
        _ = locker.lock_data


def test_extras_dependencies_are_ordered(locker: Locker, root: ProjectPackage):
    package_a = get_package("A", "1.0.0")
    package_a.add_dependency(
        Factory.create_dependency(
            "B", {"version": "^1.0.0", "optional": True, "extras": ["c", "a", "b"]}
        )
    )
    package_a.requires[-1].activate()

    locker.set_lock_data(root, [package_a])

    expected = """[[package]]
name = "A"
version = "1.0.0"
description = ""
category = "main"
optional = false
python-versions = "*"

[package.dependencies]
B = {version = "^1.0.0", extras = ["a", "b", "c"], optional = true}

[metadata]
lock-version = "1.1"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"

[metadata.files]
A = []
"""

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    assert content == expected


def test_locker_should_neither_emit_warnings_nor_raise_error_for_lower_compatible_versions(  # noqa: E501
    locker: Locker, caplog: LogCaptureFixture
):
    current_version = Version.parse(Locker._VERSION)
    older_version = ".".join(
        [str(current_version.major), str(current_version.minor - 1)]
    )
    content = f"""\
[metadata]
lock-version = "{older_version}"
python-versions = "~2.7 || ^3.4"
content-hash = "c3d07fca33fba542ef2b2a4d75bf5b48d892d21a830e2ad9c952ba5123a52f77"

[metadata.files]
"""
    caplog.set_level(logging.WARNING, logger="poetry.packages.locker")

    locker.lock.write(tomlkit.parse(content))

    _ = locker.lock_data

    assert len(caplog.records) == 0


def test_locker_dumps_dependency_information_correctly(
    locker: Locker, root: ProjectPackage
):
    root_dir = Path(__file__).parent.parent.joinpath("fixtures")
    package_a = get_package("A", "1.0.0")
    package_a.add_dependency(
        Factory.create_dependency(
            "B", {"path": "project_with_extras", "develop": True}, root_dir=root_dir
        )
    )
    package_a.add_dependency(
        Factory.create_dependency(
            "C",
            {"path": "directory/project_with_transitive_directory_dependencies"},
            root_dir=root_dir,
        )
    )
    package_a.add_dependency(
        Factory.create_dependency(
            "D", {"path": "distributions/demo-0.1.0.tar.gz"}, root_dir=root_dir
        )
    )
    package_a.add_dependency(
        Factory.create_dependency(
            "E", {"url": "https://python-poetry.org/poetry-1.2.0.tar.gz"}
        )
    )
    package_a.add_dependency(
        Factory.create_dependency(
            "F", {"git": "https://github.com/python-poetry/poetry.git", "branch": "foo"}
        )
    )

    packages = [package_a]

    locker.set_lock_data(root, packages)

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    expected = """[[package]]
name = "A"
version = "1.0.0"
description = ""
category = "main"
optional = false
python-versions = "*"

[package.dependencies]
B = {path = "project_with_extras", develop = true}
C = {path = "directory/project_with_transitive_directory_dependencies"}
D = {path = "distributions/demo-0.1.0.tar.gz"}
E = {url = "https://python-poetry.org/poetry-1.2.0.tar.gz"}
F = {git = "https://github.com/python-poetry/poetry.git", branch = "foo"}

[metadata]
lock-version = "1.1"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"

[metadata.files]
A = []
"""

    assert content == expected


def test_locked_repository_uses_root_dir_of_package(
    locker: Locker, mocker: MockerFixture
):
    content = """\
[[package]]
name = "lib-a"
version = "0.1.0"
description = ""
category = "main"
optional = false
python-versions = "^2.7.9"
develop = true

[package.dependencies]
lib-b = {path = "../libB", develop = true}

[package.source]
type = "directory"
url = "lib/libA"

[metadata]
lock-version = "1.1"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"

[metadata.files]
lib-a = []
lib-b = []
"""

    locker.lock.write(tomlkit.parse(content))
    create_dependency_patch = mocker.patch(
        "poetry.factory.Factory.create_dependency", autospec=True
    )
    locker.locked_repository()

    create_dependency_patch.assert_called_once_with(
        "lib-b", {"develop": True, "path": "../libB"}, root_dir=mocker.ANY
    )
    call_kwargs = create_dependency_patch.call_args[1]
    root_dir = call_kwargs["root_dir"]
    assert root_dir.match("*/lib/libA")
    # relative_to raises an exception if not relative - is_relative_to comes in py3.9
    assert root_dir.relative_to(locker.lock.path.parent.resolve()) is not None


@pytest.mark.parametrize(
    ("local_config", "fresh"),
    [
        ({}, True),
        ({"dependencies": [uuid.uuid4().hex]}, True),
        (
            {
                "dependencies": [uuid.uuid4().hex],
                "dev-dependencies": [uuid.uuid4().hex],
            },
            True,
        ),
        (
            {
                "dependencies": [uuid.uuid4().hex],
                "dev-dependencies": None,
            },
            True,
        ),
        ({"dependencies": [uuid.uuid4().hex], "groups": [uuid.uuid4().hex]}, False),
    ],
)
def test_content_hash_with_legacy_is_compatible(
    local_config: dict[str, list[str]], fresh: bool, locker: Locker
) -> None:
    # old hash generation
    relevant_content = {}
    for key in locker._legacy_keys:
        relevant_content[key] = local_config.get(key)

    locker = locker.__class__(
        lock=locker.lock.path,
        local_config=local_config,
    )

    old_content_hash = sha256(
        json.dumps(relevant_content, sort_keys=True).encode()
    ).hexdigest()
    content_hash = locker._get_content_hash()

    assert (content_hash == old_content_hash) or fresh
