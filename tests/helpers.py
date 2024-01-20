from __future__ import annotations

import contextlib
import os
import re
import shutil
import sys
import urllib.parse

from pathlib import Path
from typing import TYPE_CHECKING

from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link
from poetry.core.vcs.git import ParsedUrl

from poetry.config.config import Config
from poetry.console.application import Application
from poetry.factory import Factory
from poetry.installation.executor import Executor
from poetry.packages import Locker
from poetry.repositories import Repository
from poetry.repositories.exceptions import PackageNotFound
from poetry.utils._compat import metadata


if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any
    from typing import Mapping

    from poetry.core.constraints.version import Version
    from poetry.core.packages.dependency import Dependency
    from pytest_mock import MockerFixture
    from requests import Session
    from tomlkit.toml_document import TOMLDocument

    from poetry.installation.operations.operation import Operation
    from poetry.poetry import Poetry
    from poetry.utils.authenticator import Authenticator

FIXTURE_PATH = Path(__file__).parent / "fixtures"

# Used as a mock for latest git revision.
MOCK_DEFAULT_GIT_REVISION = "9cf87a285a2d3fbb0b9fa621997b3acc3631ed24"


def get_package(
    name: str, version: str | Version, yanked: str | bool = False
) -> Package:
    return Package(name, version, yanked=yanked)


def get_dependency(
    name: str,
    constraint: str | dict[str, Any] | None = None,
    groups: list[str] | None = None,
    optional: bool = False,
    allows_prereleases: bool = False,
) -> Dependency:
    if constraint is None:
        constraint = "*"

    if isinstance(constraint, str):
        constraint = {"version": constraint}

    constraint["optional"] = optional
    constraint["allow-prereleases"] = allows_prereleases

    return Factory.create_dependency(name, constraint or "*", groups=groups)


def copy_or_symlink(source: Path, dest: Path) -> None:
    if dest.is_symlink() or dest.is_file():
        dest.unlink()  # missing_ok is only available in Python >= 3.8
    elif dest.is_dir():
        shutil.rmtree(dest)

    # os.symlink requires either administrative privileges or developer mode on Win10,
    # throwing an OSError if neither is active.
    if sys.platform == "win32":
        try:
            os.symlink(str(source), str(dest), target_is_directory=source.is_dir())
        except OSError:
            if source.is_dir():
                shutil.copytree(str(source), str(dest))
            else:
                shutil.copyfile(str(source), str(dest))
    else:
        os.symlink(str(source), str(dest))


class MockDulwichRepo:
    def __init__(self, root: Path | str, **__: Any) -> None:
        self.path = str(root)

    def head(self) -> bytes:
        return MOCK_DEFAULT_GIT_REVISION.encode()


def mock_clone(
    url: str,
    *_: Any,
    source_root: Path | None = None,
    **__: Any,
) -> MockDulwichRepo:
    # Checking source to determine which folder we need to copy
    parsed = ParsedUrl.parse(url)
    assert parsed.pathname is not None
    path = re.sub(r"(.git)?$", "", parsed.pathname.lstrip("/"))

    assert parsed.resource is not None
    folder = FIXTURE_PATH / "git" / parsed.resource / path

    if not source_root:
        source_root = Path(Config.create().get("cache-dir")) / "src"

    dest = source_root / path
    dest.parent.mkdir(parents=True, exist_ok=True)

    copy_or_symlink(folder, dest)
    return MockDulwichRepo(dest)


def mock_download(
    url: str,
    dest: Path,
    *,
    session: Authenticator | Session | None = None,
    chunk_size: int = 1024,
    raise_accepts_ranges: bool = False,
) -> None:
    parts = urllib.parse.urlparse(url)

    fixture = FIXTURE_PATH / parts.path.lstrip("/")

    copy_or_symlink(fixture, dest)


class TestExecutor(Executor):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self._installs: list[Package] = []
        self._updates: list[Package] = []
        self._uninstalls: list[Package] = []

    @property
    def installations(self) -> list[Package]:
        return self._installs

    @property
    def updates(self) -> list[Package]:
        return self._updates

    @property
    def removals(self) -> list[Package]:
        return self._uninstalls

    def _do_execute_operation(self, operation: Operation) -> int:
        rc = super()._do_execute_operation(operation)

        if not operation.skipped:
            getattr(self, f"_{operation.job_type}s").append(operation.package)

        return rc

    def _execute_install(self, operation: Operation) -> int:
        return 0

    def _execute_update(self, operation: Operation) -> int:
        return 0

    def _execute_remove(self, operation: Operation) -> int:
        return 0


class PoetryTestApplication(Application):
    def __init__(self, poetry: Poetry) -> None:
        super().__init__()
        self._poetry = poetry

    def reset_poetry(self) -> None:
        assert self._poetry is not None
        poetry = self._poetry
        self._poetry = Factory().create_poetry(self._poetry.file.path.parent)
        self._poetry.set_pool(poetry.pool)
        self._poetry.set_config(poetry.config)
        self._poetry.set_locker(
            TestLocker(poetry.locker.lock, self._poetry.local_config)
        )


class TestLocker(Locker):
    # class name begins 'Test': tell pytest that it does not contain testcases.
    __test__ = False

    def __init__(self, lock: Path, local_config: dict[str, Any]) -> None:
        super().__init__(lock, local_config)
        self._locked = False
        self._write = False

    def write(self, write: bool = True) -> None:
        self._write = write

    def is_locked(self) -> bool:
        return self._locked

    def locked(self, is_locked: bool = True) -> TestLocker:
        self._locked = is_locked

        return self

    def mock_lock_data(self, data: dict[str, Any]) -> None:
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
                f"https://foo.bar/files/{package.name.replace('-', '_')}"
                f"-{package.version.to_string()}-py2.py3-none-any.whl"
            )
        ]


@contextlib.contextmanager
def isolated_environment(
    environ: dict[str, Any] | None = None, clear: bool = False
) -> Iterator[None]:
    original_environ = dict(os.environ)

    if clear:
        os.environ.clear()

    if environ:
        os.environ.update(environ)

    yield

    os.environ.clear()
    os.environ.update(original_environ)


def make_entry_point_from_plugin(
    name: str, cls: type[Any], dist: metadata.Distribution | None = None
) -> metadata.EntryPoint:
    group: str | None = getattr(cls, "group", None)
    ep = metadata.EntryPoint(
        name=name,
        group=group,  # type: ignore[arg-type]
        value=f"{cls.__module__}:{cls.__name__}",
    )

    if dist:
        ep = ep._for(dist)  # type: ignore[attr-defined,no-untyped-call]
        return ep

    return ep


def mock_metadata_entry_points(
    mocker: MockerFixture,
    cls: type[Any],
    name: str = "my-plugin",
    dist: metadata.Distribution | None = None,
) -> None:
    mocker.patch.object(
        metadata,
        "entry_points",
        return_value=[make_entry_point_from_plugin(name, cls, dist)],
    )


def flatten_dict(obj: Mapping[str, Any], delimiter: str = ".") -> Mapping[str, Any]:
    """
    Flatten a nested dict.

    A flatdict replacement.

    :param obj: A nested dict to be flattened
    :delimiter str: A delimiter used in the key path
    :return: Flattened dict
    """

    def recurse_keys(obj: Mapping[str, Any]) -> Iterator[tuple[list[str], Any]]:
        """
        A recursive generator to yield key paths and their values

        :param obj: A nested dict to be flattened
        :return:  dict
        """
        if isinstance(obj, dict):
            for key in obj:
                for leaf in recurse_keys(obj[key]):
                    leaf_path, leaf_value = leaf
                    leaf_path.insert(0, key)
                    yield (leaf_path, leaf_value)
        else:
            yield ([], obj)

    return {delimiter.join(path): value for path, value in recurse_keys(obj)}
