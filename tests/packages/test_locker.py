from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import uuid

from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from packaging.utils import canonicalize_name
from poetry.core.constraints.version import Version
from poetry.core.packages.package import Package
from poetry.core.packages.project_package import ProjectPackage

from poetry.__version__ import __version__
from poetry.factory import Factory
from poetry.packages.locker import GENERATED_COMMENT
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
        locker = Locker(Path(f.name), {})

        return locker


@pytest.fixture
def root() -> ProjectPackage:
    return ProjectPackage("root", "1.2.3")


def test_lock_file_data_is_ordered(locker: Locker, root: ProjectPackage) -> None:
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
    package_git_with_subdirectory = Package(
        "git-package-subdir",
        "1.2.3",
        source_type="git",
        source_url="https://github.com/python-poetry/poetry.git",
        source_reference="develop",
        source_resolved_reference="123456",
        source_subdirectory="subdir",
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
        package_git_with_subdirectory,
        package_url_win32,
        package_url_linux,
    ]

    locker.set_lock_data(root, packages)

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    expected = f"""\
# {GENERATED_COMMENT}

[[package]]
name = "A"
version = "1.0.0"
description = ""
optional = false
python-versions = "*"
files = [
    {{file = "bar", hash = "123"}},
    {{file = "foo", hash = "456"}},
]

[package.dependencies]
B = "^1.0"

[[package]]
name = "A"
version = "2.0.0"
description = ""
optional = false
python-versions = "*"
files = [
    {{file = "baz", hash = "345"}},
]

[[package]]
name = "B"
version = "1.2"
description = ""
optional = false
python-versions = "*"
files = []

[[package]]
name = "git-package"
version = "1.2.3"
description = ""
optional = false
python-versions = "*"
files = []
develop = false

[package.source]
type = "git"
url = "https://github.com/python-poetry/poetry.git"
reference = "develop"
resolved_reference = "123456"

[[package]]
name = "git-package-subdir"
version = "1.2.3"
description = ""
optional = false
python-versions = "*"
files = []
develop = false

[package.source]
type = "git"
url = "https://github.com/python-poetry/poetry.git"
reference = "develop"
resolved_reference = "123456"
subdirectory = "subdir"

[[package]]
name = "url-package"
version = "1.0"
description = ""
optional = false
python-versions = "*"
files = []

[package.source]
type = "url"
url = "https://example.org/url-package-1.0-cp39-manylinux_2_17_x86_64.whl"

[[package]]
name = "url-package"
version = "1.0"
description = ""
optional = false
python-versions = "*"
files = []

[package.source]
type = "url"
url = "https://example.org/url-package-1.0-cp39-win_amd64.whl"

[metadata]
lock-version = "2.0"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
"""

    assert content == expected


def test_locker_properly_loads_extras(locker: Locker) -> None:
    content = f"""\
# {GENERATED_COMMENT}

[[package]]
name = "cachecontrol"
version = "0.12.5"
description = "httplib2 caching for requests"
optional = false
python-versions = ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*"
files = []

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
lock-version = "2.0"
python-versions = "~2.7 || ^3.4"
content-hash = "c3d07fca33fba542ef2b2a4d75bf5b48d892d21a830e2ad9c952ba5123a52f77"
"""

    with open(locker.lock, "w", encoding="utf-8") as f:
        f.write(content)

    packages = locker.locked_repository().packages

    assert len(packages) == 1

    package = packages[0]
    assert len(package.requires) == 3
    assert len(package.extras) == 2

    lockfile_dep = package.extras[canonicalize_name("filecache")][0]
    assert lockfile_dep.name == "lockfile"


def test_locker_properly_loads_nested_extras(locker: Locker) -> None:
    content = f"""\
# {GENERATED_COMMENT}

[[package]]
name = "a"
version = "1.0"
description = ""
optional = false
python-versions = "*"
files = []

[package.dependencies]
b = {{version = "^1.0", optional = true, extras = "c"}}

[package.extras]
b = ["b[c] (>=1.0,<2.0)"]

[[package]]
name = "b"
version = "1.0"
description = ""
optional = false
python-versions = "*"
files = []

[package.dependencies]
c = {{version = "^1.0", optional = true}}

[package.extras]
c = ["c (>=1.0,<2.0)"]

[[package]]
name = "c"
version = "1.0"
description = ""
optional = false
python-versions = "*"
files = []

[metadata]
python-versions = "*"
lock-version = "2.0"
content-hash = "123456789"
"""

    with open(locker.lock, "w", encoding="utf-8") as f:
        f.write(content)

    repository = locker.locked_repository()
    assert len(repository.packages) == 3

    packages = repository.find_packages(get_dependency("a", "1.0"))
    assert len(packages) == 1

    package = packages[0]
    assert len(package.requires) == 1
    assert len(package.extras) == 1

    dependency_b = package.extras[canonicalize_name("b")][0]
    assert dependency_b.name == "b"
    assert dependency_b.extras == frozenset({"c"})

    packages = repository.find_packages(dependency_b)
    assert len(packages) == 1

    package = packages[0]
    assert len(package.requires) == 1
    assert len(package.extras) == 1

    dependency_c = package.extras[canonicalize_name("c")][0]
    assert dependency_c.name == "c"
    assert dependency_c.extras == frozenset()

    packages = repository.find_packages(dependency_c)
    assert len(packages) == 1


def test_locker_properly_loads_extras_legacy(locker: Locker) -> None:
    content = f"""\
# {GENERATED_COMMENT}

[[package]]
name = "a"
version = "1.0"
description = ""
optional = false
python-versions = "*"
files = []

[package.dependencies]
b = {{version = "^1.0", optional = true}}

[package.extras]
b = ["b (^1.0)"]

[[package]]
name = "b"
version = "1.0"
description = ""
optional = false
python-versions = "*"
files = []

[metadata]
python-versions = "*"
lock-version = "2.0"
content-hash = "123456789"
"""

    with open(locker.lock, "w", encoding="utf-8") as f:
        f.write(content)

    repository = locker.locked_repository()
    assert len(repository.packages) == 2

    packages = repository.find_packages(get_dependency("a", "1.0"))
    assert len(packages) == 1

    package = packages[0]
    assert len(package.requires) == 1
    assert len(package.extras) == 1

    dependency_b = package.extras[canonicalize_name("b")][0]
    assert dependency_b.name == "b"


def test_locker_properly_loads_subdir(locker: Locker) -> None:
    content = """\
[[package]]
name = "git-package-subdir"
version = "1.2.3"
description = ""
optional = false
python-versions = "*"
develop = false
files = []

[package.source]
type = "git"
url = "https://github.com/python-poetry/poetry.git"
reference = "develop"
resolved_reference = "123456"
subdirectory = "subdir"

[metadata]
lock-version = "2.0"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
"""
    with open(locker.lock, "w", encoding="utf-8") as f:
        f.write(content)

    repository = locker.locked_repository()
    assert len(repository.packages) == 1

    packages = repository.find_packages(get_dependency("git-package-subdir", "1.2.3"))
    assert len(packages) == 1

    package = packages[0]
    assert package.source_subdirectory == "subdir"


def test_locker_properly_assigns_metadata_files(locker: Locker) -> None:
    """
    For multiple constraints dependencies, there is only one common entry in
    metadata.files. However, we must not assign all the files to each of the packages
    because this can result in duplicated and outdated entries when running
    `poetry lock --no-update` and hash check failures when running `poetry install`.
    """
    content = """\
[[package]]
name = "demo"
version = "1.0"
description = ""
optional = false
python-versions = "*"
develop = false

[[package]]
name = "demo"
version = "1.0"
description = ""
optional = false
python-versions = "*"
develop = false

[package.source]
type = "git"
url = "https://github.com/demo/demo.git"
reference = "main"
resolved_reference = "123456"

[[package]]
name = "demo"
version = "1.0"
description = ""
optional = false
python-versions = "*"
develop = false

[package.source]
type = "directory"
url = "./folder"

[[package]]
name = "demo"
version = "1.0"
description = ""
optional = false
python-versions = "*"
develop = false

[package.source]
type = "file"
url = "./demo-1.0-cp39-win_amd64.whl"

[[package]]
name = "demo"
version = "1.0"
description = ""
optional = false
python-versions = "*"
develop = false

[package.source]
type = "url"
url = "https://example.com/demo-1.0-cp38-win_amd64.whl"

[metadata]
lock-version = "1.1"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"

[metadata.files]
# metadata.files are only tracked for non-direct origin and file dependencies
demo = [
    {file = "demo-1.0-cp39-win_amd64.whl", hash = "sha256"},
    {file = "demo-1.0.tar.gz", hash = "sha256"},
    {file = "demo-1.0-py3-none-any.whl", hash = "sha256"},
]
"""
    with open(locker.lock, "w", encoding="utf-8") as f:
        f.write(content)

    repository = locker.locked_repository()
    assert len(repository.packages) == 5
    assert {package.source_type for package in repository.packages} == {
        None,
        "git",
        "directory",
        "file",
        "url",
    }
    for package in repository.packages:
        if package.source_type is None:
            # non-direct origin package contains all files
            # with the current lockfile format we have no chance to determine
            # which files are correct, so we keep all for hash check
            # correct files are set later in Provider.complete_package()
            assert package.files == [
                {"file": "demo-1.0-cp39-win_amd64.whl", "hash": "sha256"},
                {"file": "demo-1.0.tar.gz", "hash": "sha256"},
                {"file": "demo-1.0-py3-none-any.whl", "hash": "sha256"},
            ]
        elif package.source_type == "file":
            assert package.files == [
                {"file": "demo-1.0-cp39-win_amd64.whl", "hash": "sha256"}
            ]
        else:
            package.files = []


def test_lock_packages_with_null_description(
    locker: Locker, root: ProjectPackage
) -> None:
    package_a = get_package("A", "1.0.0")
    package_a.description = None  # type: ignore[assignment]

    locker.set_lock_data(root, [package_a])

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    expected = f"""\
# {GENERATED_COMMENT}

[[package]]
name = "A"
version = "1.0.0"
description = ""
optional = false
python-versions = "*"
files = []

[metadata]
lock-version = "2.0"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
"""

    assert content == expected


def test_lock_file_should_not_have_mixed_types(
    locker: Locker, root: ProjectPackage
) -> None:
    package_a = get_package("A", "1.0.0")
    package_a.add_dependency(Factory.create_dependency("B", "^1.0.0"))
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": ">=1.0.0", "optional": True})
    )
    package_a.requires[-1].activate()
    package_a.extras = {canonicalize_name("foo"): [get_dependency("B", ">=1.0.0")]}

    locker.set_lock_data(root, [package_a])

    expected = f"""\
# {GENERATED_COMMENT}

[[package]]
name = "A"
version = "1.0.0"
description = ""
optional = false
python-versions = "*"
files = []

[package.dependencies]
B = [
    {{version = "^1.0.0"}},
    {{version = ">=1.0.0", optional = true}},
]

[package.extras]
foo = ["B (>=1.0.0)"]

[metadata]
lock-version = "2.0"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
"""

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    assert content == expected


def test_reading_lock_file_should_raise_an_error_on_invalid_data(
    locker: Locker,
) -> None:
    content = f"""\
# {GENERATED_COMMENT}

[[package]]
name = "A"
version = "1.0.0"
description = ""
optional = false
python-versions = "*"
files = []

[package.extras]
foo = ["bar"]

[package.extras]
foo = ["bar"]

[metadata]
lock-version = "2.0"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
"""
    with locker.lock.open("w", encoding="utf-8") as f:
        f.write(content)

    with pytest.raises(RuntimeError) as e:
        _ = locker.lock_data

    assert "Unable to read the lock file" in str(e.value)


def test_reading_lock_file_should_raise_an_error_on_missing_metadata(
    locker: Locker,
) -> None:
    content = f"""\
# {GENERATED_COMMENT}

[[package]]
name = "A"
version = "1.0.0"
description = ""
optional = false
python-versions = "*"
files = []

[package.source]
type = "legacy"
url = "https://foo.bar"
reference = "legacy"
"""
    with locker.lock.open("w", encoding="utf-8") as f:
        f.write(content)

    with pytest.raises(RuntimeError) as e:
        _ = locker.lock_data

    assert (
        "The lock file does not have a metadata entry.\nRegenerate the lock file with"
        " the `poetry lock` command." in str(e.value)
    )


def test_locking_legacy_repository_package_should_include_source_section(
    root: ProjectPackage, locker: Locker
) -> None:
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

    expected = f"""\
# {GENERATED_COMMENT}

[[package]]
name = "A"
version = "1.0.0"
description = ""
optional = false
python-versions = "*"
files = []

[package.source]
type = "legacy"
url = "https://foo.bar"
reference = "legacy"

[metadata]
lock-version = "2.0"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
"""

    assert content == expected


def test_locker_should_emit_warnings_if_lock_version_is_newer_but_allowed(
    locker: Locker, caplog: LogCaptureFixture
) -> None:
    version = ".".join(Version.parse(Locker._VERSION).next_minor().text.split(".")[:2])
    content = f"""\
[metadata]
lock-version = "{version}"
python-versions = "~2.7 || ^3.4"
content-hash = "c3d07fca33fba542ef2b2a4d75bf5b48d892d21a830e2ad9c952ba5123a52f77"
"""
    caplog.set_level(logging.WARNING, logger="poetry.packages.locker")

    with open(locker.lock, "w", encoding="utf-8") as f:
        f.write(content)

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
) -> None:
    content = f"""\
# {GENERATED_COMMENT}

[metadata]
lock-version = "3.0"
python-versions = "~2.7 || ^3.4"
content-hash = "c3d07fca33fba542ef2b2a4d75bf5b48d892d21a830e2ad9c952ba5123a52f77"
"""
    caplog.set_level(logging.WARNING, logger="poetry.packages.locker")

    with open(locker.lock, "w", encoding="utf-8") as f:
        f.write(content)

    with pytest.raises(RuntimeError, match="^The lock file is not compatible"):
        _ = locker.lock_data


def test_root_extras_dependencies_are_ordered(
    locker: Locker, root: ProjectPackage, fixture_base: Path
) -> None:
    Factory.create_dependency("B", "1.0.0", root_dir=fixture_base)
    Factory.create_dependency("C", "1.0.0", root_dir=fixture_base)
    package_first = Factory.create_dependency("first", "1.0.0", root_dir=fixture_base)
    package_second = Factory.create_dependency("second", "1.0.0", root_dir=fixture_base)
    package_third = Factory.create_dependency("third", "1.0.0", root_dir=fixture_base)

    root.extras = {
        canonicalize_name("C"): [package_third, package_second, package_first],
        canonicalize_name("B"): [package_first, package_second, package_third],
    }
    locker.set_lock_data(root, [])

    expected = f"""\
# {GENERATED_COMMENT}
package = []

[extras]
b = ["first", "second", "third"]
c = ["first", "second", "third"]

[metadata]
lock-version = "2.0"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
"""

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    print(content)
    assert content == expected


def test_extras_dependencies_are_ordered(locker: Locker, root: ProjectPackage) -> None:
    package_a = get_package("A", "1.0.0")
    package_a.add_dependency(
        Factory.create_dependency(
            "B", {"version": "^1.0.0", "optional": True, "extras": ["c", "a", "b"]}
        )
    )
    package_a.requires[-1].activate()

    locker.set_lock_data(root, [package_a])

    expected = f"""\
# {GENERATED_COMMENT}

[[package]]
name = "A"
version = "1.0.0"
description = ""
optional = false
python-versions = "*"
files = []

[package.dependencies]
B = {{version = "^1.0.0", extras = ["a", "b", "c"], optional = true}}

[metadata]
lock-version = "2.0"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
"""

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    assert content == expected


def test_locker_should_neither_emit_warnings_nor_raise_error_for_lower_compatible_versions(
    locker: Locker, caplog: LogCaptureFixture
) -> None:
    older_version = "1.1"
    content = f"""\
[metadata]
lock-version = "{older_version}"
python-versions = "~2.7 || ^3.4"
content-hash = "c3d07fca33fba542ef2b2a4d75bf5b48d892d21a830e2ad9c952ba5123a52f77"

[metadata.files]
"""
    caplog.set_level(logging.WARNING, logger="poetry.packages.locker")

    with open(locker.lock, "w", encoding="utf-8") as f:
        f.write(content)

    _ = locker.lock_data

    assert len(caplog.records) == 0


def test_locker_dumps_dependency_information_correctly(
    locker: Locker, root: ProjectPackage, fixture_base: Path
) -> None:
    package_a = get_package("A", "1.0.0")
    package_a.add_dependency(
        Factory.create_dependency(
            "B", {"path": "project_with_extras", "develop": True}, root_dir=fixture_base
        )
    )
    package_a.add_dependency(
        Factory.create_dependency(
            "C",
            {"path": "directory/project_with_transitive_directory_dependencies"},
            root_dir=fixture_base,
        )
    )
    package_a.add_dependency(
        Factory.create_dependency(
            "D", {"path": "distributions/demo-0.1.0.tar.gz"}, root_dir=fixture_base
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
    package_a.add_dependency(
        Factory.create_dependency(
            "G",
            {
                "git": "https://github.com/python-poetry/poetry.git",
                "subdirectory": "bar",
            },
        )
    )
    package_a.add_dependency(
        Factory.create_dependency(
            "H", {"git": "https://github.com/python-poetry/poetry.git", "tag": "baz"}
        )
    )
    package_a.add_dependency(
        Factory.create_dependency(
            "I", {"git": "https://github.com/python-poetry/poetry.git", "rev": "spam"}
        )
    )

    packages = [package_a]

    locker.set_lock_data(root, packages)

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    expected = f"""\
# {GENERATED_COMMENT}

[[package]]
name = "A"
version = "1.0.0"
description = ""
optional = false
python-versions = "*"
files = []

[package.dependencies]
B = {{path = "project_with_extras", develop = true}}
C = {{path = "directory/project_with_transitive_directory_dependencies"}}
D = {{path = "distributions/demo-0.1.0.tar.gz"}}
E = {{url = "https://python-poetry.org/poetry-1.2.0.tar.gz"}}
F = {{git = "https://github.com/python-poetry/poetry.git", branch = "foo"}}
G = {{git = "https://github.com/python-poetry/poetry.git", subdirectory = "bar"}}
H = {{git = "https://github.com/python-poetry/poetry.git", tag = "baz"}}
I = {{git = "https://github.com/python-poetry/poetry.git", rev = "spam"}}

[metadata]
lock-version = "2.0"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
"""

    assert content == expected


def test_locker_dumps_subdir(locker: Locker, root: ProjectPackage) -> None:
    package_git_with_subdirectory = Package(
        "git-package-subdir",
        "1.2.3",
        source_type="git",
        source_url="https://github.com/python-poetry/poetry.git",
        source_reference="develop",
        source_resolved_reference="123456",
        source_subdirectory="subdir",
    )

    locker.set_lock_data(root, [package_git_with_subdirectory])

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    expected = f"""\
# {GENERATED_COMMENT}

[[package]]
name = "git-package-subdir"
version = "1.2.3"
description = ""
optional = false
python-versions = "*"
files = []
develop = false

[package.source]
type = "git"
url = "https://github.com/python-poetry/poetry.git"
reference = "develop"
resolved_reference = "123456"
subdirectory = "subdir"

[metadata]
lock-version = "2.0"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
"""

    assert content == expected


def test_locker_dumps_dependency_extras_in_correct_order(
    locker: Locker, root: ProjectPackage, fixture_base: Path
) -> None:
    package_a = get_package("A", "1.0.0")
    Factory.create_dependency("B", "1.0.0", root_dir=fixture_base)
    Factory.create_dependency("C", "1.0.0", root_dir=fixture_base)
    package_first = Factory.create_dependency("first", "1.0.0", root_dir=fixture_base)
    package_second = Factory.create_dependency("second", "1.0.0", root_dir=fixture_base)
    package_third = Factory.create_dependency("third", "1.0.0", root_dir=fixture_base)

    package_a.extras = {
        canonicalize_name("C"): [package_third, package_second, package_first],
        canonicalize_name("B"): [package_first, package_second, package_third],
    }

    locker.set_lock_data(root, [package_a])

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    expected = f"""\
# {GENERATED_COMMENT}

[[package]]
name = "A"
version = "1.0.0"
description = ""
optional = false
python-versions = "*"
files = []

[package.extras]
b = ["first (==1.0.0)", "second (==1.0.0)", "third (==1.0.0)"]
c = ["first (==1.0.0)", "second (==1.0.0)", "third (==1.0.0)"]

[metadata]
lock-version = "2.0"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
"""

    assert content == expected


def test_locked_repository_uses_root_dir_of_package(
    locker: Locker, mocker: MockerFixture
) -> None:
    content = f"""\
# {GENERATED_COMMENT}

[[package]]
name = "lib-a"
version = "0.1.0"
description = ""
optional = false
python-versions = "^2.7.9"
develop = true
file = []

[package.dependencies]
lib-b = {{path = "../libB", develop = true}}

[package.source]
type = "directory"
url = "lib/libA"

[metadata]
lock-version = "2.0"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
"""

    with open(locker.lock, "w", encoding="utf-8") as f:
        f.write(content)

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
    assert root_dir.relative_to(locker.lock.parent.resolve()) is not None


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
        lock=locker.lock,
        local_config=local_config,
    )

    old_content_hash = sha256(
        json.dumps(relevant_content, sort_keys=True).encode()
    ).hexdigest()
    content_hash = locker._get_content_hash()

    assert (content_hash == old_content_hash) or fresh


def test_lock_file_resolves_file_url_symlinks(root: ProjectPackage) -> None:
    """
    Create directories and file structure as follows:

    d1/
    d1/testsymlink -> d1/d2/d3
    d1/d2/d3/lock_file
    d1/d4/source_file

    Using the testsymlink as the Locker.lock file path should correctly resolve to
    the real physical path of the source_file when calculating the relative path
    from the lock_file, i.e. "../../d4/source_file" instead of the unresolved path
    from the symlink itself which would have been "../d4/source_file"

    See https://github.com/python-poetry/poetry/issues/5849
    """
    with tempfile.TemporaryDirectory() as d1:
        symlink_path = Path(d1).joinpath("testsymlink")
        with tempfile.TemporaryDirectory(dir=d1) as d2, tempfile.TemporaryDirectory(
            dir=d1
        ) as d4, tempfile.TemporaryDirectory(dir=d2) as d3, tempfile.NamedTemporaryFile(
            dir=d4
        ) as source_file, tempfile.NamedTemporaryFile(
            dir=d3
        ) as lock_file:
            lock_file.close()
            try:
                os.symlink(Path(d3), symlink_path)
            except OSError:
                if sys.platform == "win32":
                    # os.symlink requires either administrative privileges or developer
                    # mode on Win10, throwing an OSError if neither is active.
                    # Test is not possible in that case.
                    return
                raise
            locker = Locker(symlink_path / lock_file.name, {})

            package_local = Package(
                "local-package",
                "1.2.3",
                source_type="file",
                source_url=source_file.name,
                source_reference="develop",
                source_resolved_reference="123456",
            )
            packages = [
                package_local,
            ]

            locker.set_lock_data(root, packages)

            with locker.lock.open(encoding="utf-8") as f:
                content = f.read()

            expected = f"""\
# {GENERATED_COMMENT}

[[package]]
name = "local-package"
version = "1.2.3"
description = ""
optional = false
python-versions = "*"
files = []

[package.source]
type = "file"
url = "{
    Path(
        os.path.relpath(
            Path(source_file.name).resolve().as_posix(),
            Path(Path(lock_file.name).parent).resolve().as_posix(),
        )
    ).as_posix()
}"
reference = "develop"
resolved_reference = "123456"

[metadata]
lock-version = "2.0"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
"""

            assert content == expected


def test_lockfile_is_not_rewritten_if_only_poetry_version_changed(
    locker: Locker, root: ProjectPackage
) -> None:
    generated_comment_old_version = GENERATED_COMMENT.replace(__version__, "1.3.2")
    assert generated_comment_old_version != GENERATED_COMMENT
    old_content = f"""\
# {generated_comment_old_version}
package = []

[metadata]
lock-version = "2.0"
python-versions = "*"
content-hash = "115cf985d932e9bf5f540555bbdd75decbb62cac81e399375fc19f6277f8c1d8"
"""

    with open(locker.lock, "w", encoding="utf-8") as f:
        f.write(old_content)

    assert not locker.set_lock_data(root, [])

    with locker.lock.open(encoding="utf-8") as f:
        content = f.read()

    assert content == old_content
