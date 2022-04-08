from __future__ import annotations

import os
import re
import shutil
import urllib.parse

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from poetry.core.masonry.utils.helpers import escape_name
from poetry.core.masonry.utils.helpers import escape_version
from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link
from poetry.core.toml.file import TOMLFile
from poetry.core.vcs.git import ParsedUrl

from poetry.console.application import Application
from poetry.factory import Factory
from poetry.installation.executor import Executor
from poetry.packages import Locker
from poetry.repositories import Repository
from poetry.repositories.exceptions import PackageNotFound


if TYPE_CHECKING:
    from poetry.core.packages.dependency import Dependency
    from poetry.core.packages.types import DependencyTypes
    from poetry.core.semver.version import Version
    from tomlkit.toml_document import TOMLDocument

    from poetry.installation.operations import OperationTypes
    from poetry.poetry import Poetry

FIXTURE_PATH = Path(__file__).parent / "fixtures"


def get_package(name: str, version: str | Version) -> Package:
    return Package(name, version)


def get_dependency(
    name: str,
    constraint: str | dict[str, Any] | None = None,
    groups: list[str] | None = None,
    optional: bool = False,
    allows_prereleases: bool = False,
) -> DependencyTypes:
    if constraint is None:
        constraint = "*"

    if isinstance(constraint, str):
        constraint = {"version": constraint}

    constraint["optional"] = optional
    constraint["allow-prereleases"] = allows_prereleases

    return Factory.create_dependency(name, constraint or "*", groups=groups)


def fixture(path: str | None = None) -> Path:
    if path:
        return FIXTURE_PATH / path
    else:
        return FIXTURE_PATH


def copy_or_symlink(source: Path, dest: Path) -> None:
    if dest.is_symlink() or dest.is_file():
        dest.unlink()  # missing_ok is only available in Python >= 3.8
    elif dest.is_dir():
        shutil.rmtree(dest)

    os.symlink(str(source), str(dest), target_is_directory=source.is_dir())


class MockDulwichRepo:
    def __init__(self, root: Path | str, **__: Any) -> None:
        self.path = str(root)

    def head(self) -> bytes:
        return b"9cf87a285a2d3fbb0b9fa621997b3acc3631ed24"


def mock_clone(
    url: str,
    *_: Any,
    source_root: Path | None = None,
    **__: Any,
) -> MockDulwichRepo:
    # Checking source to determine which folder we need to copy
    parsed = ParsedUrl.parse(url)
    path = re.sub(r"(.git)?$", "", parsed.pathname.lstrip("/"))

    folder = Path(__file__).parent / "fixtures" / "git" / parsed.resource / path

    if not source_root:
        source_root = Path(Factory.create_config().get("cache-dir")) / "src"

    dest = source_root / path
    dest.parent.mkdir(parents=True, exist_ok=True)

    copy_or_symlink(folder, dest)
    return MockDulwichRepo(dest)


def mock_download(url: str, dest: str, **__: Any) -> None:
    parts = urllib.parse.urlparse(url)

    fixtures = Path(__file__).parent / "fixtures"
    fixture = fixtures / parts.path.lstrip("/")

    copy_or_symlink(fixture, Path(dest))


class TestExecutor(Executor):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self._installs = []
        self._updates = []
        self._uninstalls = []

    @property
    def installations(self) -> list[Package]:
        return self._installs

    @property
    def updates(self) -> list[Package]:
        return self._updates

    @property
    def removals(self) -> list[Package]:
        return self._uninstalls

    def _do_execute_operation(self, operation: OperationTypes) -> None:
        super()._do_execute_operation(operation)

        if not operation.skipped:
            getattr(self, f"_{operation.job_type}s").append(operation.package)

    def _execute_install(self, operation: OperationTypes) -> int:
        return 0

    def _execute_update(self, operation: OperationTypes) -> int:
        return 0

    def _execute_remove(self, operation: OperationTypes) -> int:
        return 0


class PoetryTestApplication(Application):
    def __init__(self, poetry: Poetry):
        super().__init__()
        self._poetry = poetry

    def reset_poetry(self) -> None:
        poetry = self._poetry
        self._poetry = Factory().create_poetry(self._poetry.file.path.parent)
        self._poetry.set_pool(poetry.pool)
        self._poetry.set_config(poetry.config)
        self._poetry.set_locker(
            TestLocker(poetry.locker.lock.path, self._poetry.local_config)
        )


class TestLocker(Locker):
    def __init__(self, lock: str | Path, local_config: dict):
        self._lock = TOMLFile(lock)
        self._local_config = local_config
        self._lock_data = None
        self._content_hash = self._get_content_hash()
        self._locked = False
        self._lock_data = None
        self._write = False

    def write(self, write: bool = True) -> None:
        self._write = write

    def is_locked(self) -> bool:
        return self._locked

    def locked(self, is_locked: bool = True) -> TestLocker:
        self._locked = is_locked

        return self

    def mock_lock_data(self, data: dict) -> None:
        self.locked()

        self._lock_data = data

    def is_fresh(self) -> bool:
        return True

    def _write_lock_data(self, data: TOMLDocument) -> None:
        if self._write:
            super()._write_lock_data(data)
            self._locked = True
            return

        self._lock_data = data


class TestRepository(Repository):
    def find_packages(self, dependency: Dependency) -> list[Package]:
        packages = super().find_packages(dependency)
        if len(packages) == 0:
            raise PackageNotFound(f"Package [{dependency.name}] not found.")

        return packages

    def find_links_for_package(self, package: Package) -> list[Link]:
        return [
            Link(
                f"https://foo.bar/files/{escape_name(package.name)}"
                f"-{escape_version(package.version.text)}-py2.py3-none-any.whl"
            )
        ]
