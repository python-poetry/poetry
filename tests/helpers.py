import os
import shutil
import urllib.parse

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

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
from poetry.utils._compat import WINDOWS


if TYPE_CHECKING:
    from poetry.core.packages.dependency import Dependency
    from poetry.core.packages.types import DependencyTypes
    from poetry.core.semver.version import Version
    from tomlkit.toml_document import TOMLDocument

    from poetry.installation.operations import OperationTypes
    from poetry.poetry import Poetry

FIXTURE_PATH = Path(__file__).parent / "fixtures"


def get_package(name: str, version: Union[str, "Version"]) -> Package:
    return Package(name, version)


def get_dependency(
    name: str,
    constraint: Optional[Union[str, Dict[str, Any]]] = None,
    groups: Optional[List[str]] = None,
    optional: bool = False,
    allows_prereleases: bool = False,
) -> "DependencyTypes":
    if constraint is None:
        constraint = "*"

    if isinstance(constraint, str):
        constraint = {"version": constraint}

    constraint["optional"] = optional
    constraint["allow_prereleases"] = allows_prereleases

    return Factory.create_dependency(name, constraint or "*", groups=groups)


def fixture(path: Optional[str] = None) -> Path:
    if path:
        return FIXTURE_PATH / path
    else:
        return FIXTURE_PATH


def copy_or_symlink(source: Path, dest: Path) -> None:
    if dest.exists():
        if dest.is_symlink():
            os.unlink(str(dest))
        elif dest.is_dir():
            shutil.rmtree(str(dest))
        else:
            os.unlink(str(dest))

    # Python2 does not support os.symlink on Windows whereas Python3 does.
    # os.symlink requires either administrative privileges or developer mode on Win10,
    # throwing an OSError if neither is active.
    if WINDOWS:
        try:
            os.symlink(str(source), str(dest), target_is_directory=source.is_dir())
        except OSError:
            if source.is_dir():
                shutil.copytree(str(source), str(dest))
            else:
                shutil.copyfile(str(source), str(dest))
    else:
        os.symlink(str(source), str(dest))


def mock_clone(_: Any, source: str, dest: Path) -> None:
    # Checking source to determine which folder we need to copy
    parsed = ParsedUrl.parse(source)

    folder = (
        Path(__file__).parent
        / "fixtures"
        / "git"
        / parsed.resource
        / parsed.pathname.lstrip("/").rstrip(".git")
    )

    copy_or_symlink(folder, dest)


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
    def installations(self) -> List[Package]:
        return self._installs

    @property
    def updates(self) -> List[Package]:
        return self._updates

    @property
    def removals(self) -> List[Package]:
        return self._uninstalls

    def _do_execute_operation(self, operation: "OperationTypes") -> None:
        super()._do_execute_operation(operation)

        if not operation.skipped:
            getattr(self, f"_{operation.job_type}s").append(operation.package)

    def _execute_install(self, operation: "OperationTypes") -> int:
        return 0

    def _execute_update(self, operation: "OperationTypes") -> int:
        return 0

    def _execute_remove(self, operation: "OperationTypes") -> int:
        return 0


class PoetryTestApplication(Application):
    def __init__(self, poetry: "Poetry"):
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
    def __init__(self, lock: Union[str, Path], local_config: Dict):
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

    def locked(self, is_locked: bool = True) -> "TestLocker":
        self._locked = is_locked

        return self

    def mock_lock_data(self, data: Dict) -> None:
        self.locked()

        self._lock_data = data

    def is_fresh(self) -> bool:
        return True

    def _write_lock_data(self, data: "TOMLDocument") -> None:
        if self._write:
            super()._write_lock_data(data)
            self._locked = True
            return

        self._lock_data = data


class TestRepository(Repository):
    def find_packages(self, dependency: "Dependency") -> List[Package]:
        packages = super().find_packages(dependency)
        if len(packages) == 0:
            raise PackageNotFound(f"Package [{dependency.name}] not found.")

        return packages

    def find_links_for_package(self, package: Package) -> List[Link]:
        return [
            Link(
                f"https://foo.bar/files/{escape_name(package.name)}"
                f"-{escape_version(package.version.text)}-py2.py3-none-any.whl"
            )
        ]
