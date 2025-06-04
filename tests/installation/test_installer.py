from __future__ import annotations

import json
import re
import shutil

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import pytest

from cleo.io.buffered_io import BufferedIO
from cleo.io.inputs.input import Input
from cleo.io.null_io import NullIO
from cleo.io.outputs.output import Verbosity
from packaging.utils import canonicalize_name
from poetry.core.constraints.version import Version
from poetry.core.packages.dependency_group import MAIN_GROUP
from poetry.core.packages.dependency_group import DependencyGroup
from poetry.core.packages.package import Package
from poetry.core.packages.project_package import ProjectPackage

from poetry.factory import Factory
from poetry.installation import Installer
from poetry.packages import Locker as BaseLocker
from poetry.repositories import Repository
from poetry.repositories import RepositoryPool
from poetry.repositories.installed_repository import InstalledRepository
from poetry.toml.file import TOMLFile
from poetry.utils.env import MockEnv
from poetry.utils.env import NullEnv
from tests.helpers import MOCK_DEFAULT_GIT_REVISION
from tests.helpers import TestExecutor
from tests.helpers import get_dependency
from tests.helpers import get_package


if TYPE_CHECKING:
    from collections.abc import Iterator

    from _pytest.fixtures import FixtureRequest
    from pytest_mock import MockerFixture
    from tomlkit import TOMLDocument

    from poetry.repositories.legacy_repository import LegacyRepository
    from poetry.repositories.pypi_repository import PyPiRepository
    from poetry.utils.env import Env
    from tests.conftest import Config
    from tests.types import FixtureDirGetter
    from tests.types import PackageFactory


class CustomInstalledRepository(InstalledRepository):
    @classmethod
    def load(
        cls, env: Env, with_dependencies: bool = False
    ) -> CustomInstalledRepository:
        return cls()


class Locker(BaseLocker):
    def __init__(self, lock_path: Path) -> None:
        self._lock = lock_path / "poetry.lock"
        self._written_data = None
        self._locked = False
        self._fresh = True
        self._lock_data = None
        self._content_hash = self._get_content_hash()

    @property
    def written_data(self) -> dict[str, Any]:
        assert self._written_data is not None
        return self._written_data

    def set_lock_path(self, lock: Path) -> Locker:
        self._lock = lock / "poetry.lock"

        return self

    def locked(self, is_locked: bool = True) -> Locker:
        self._locked = is_locked

        return self

    def mock_lock_data(self, data: dict[str, Any]) -> None:
        self._lock_data = data

    def is_locked(self) -> bool:
        return self._locked

    def fresh(self, is_fresh: bool = True) -> Locker:
        self._fresh = is_fresh

        return self

    def is_fresh(self) -> bool:
        return self._fresh

    def _get_content_hash(self) -> str:
        return "123456789"

    def _write_lock_data(self, data: dict[str, Any]) -> None:
        for package in data["package"]:
            python_versions = str(package["python-versions"])
            package["python-versions"] = python_versions

        self._written_data = json.loads(json.dumps(data))
        self._lock_data = data


@pytest.fixture(autouse=True, params=[False, True])
def config_installer_reresolve(
    config: Config, request: FixtureRequest
) -> Iterator[bool]:
    config.config["installer"]["re-resolve"] = request.param
    yield request.param


@pytest.fixture()
def package() -> ProjectPackage:
    p = ProjectPackage("root", "1.0")
    p.root_dir = Path.cwd()

    return p


@pytest.fixture()
def repo() -> Repository:
    return Repository("repo")


@pytest.fixture()
def pool(repo: Repository) -> RepositoryPool:
    pool = RepositoryPool()
    pool.add_repository(repo)

    return pool


@pytest.fixture()
def installed() -> CustomInstalledRepository:
    return CustomInstalledRepository()


@pytest.fixture()
def locker(project_root: Path) -> Locker:
    return Locker(lock_path=project_root)


@pytest.fixture()
def env(tmp_path: Path) -> NullEnv:
    return NullEnv(path=tmp_path)


@pytest.fixture()
def installer(
    package: ProjectPackage,
    pool: RepositoryPool,
    locker: Locker,
    env: NullEnv,
    installed: CustomInstalledRepository,
    config: Config,
) -> Installer:
    return Installer(
        NullIO(),
        env,
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=TestExecutor(env, pool, config, NullIO()),
    )


def fixture(name: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Create or load a fixture file in TOML format.

    This function retrieves the contents of a test fixture file, optionally writing
    data to it before reading, and returns the data as a dictionary. It is used to
    manage testing fixtures for TOML-based configurations.

    :param name: Name of the fixture file (without extension, default of .test is appended).
    :param data: Dictionary to write to the file as a TOML document. If None,
                 no data is written (use this only when generating fixtures).
    :return: Dictionary representing the contents of the TOML fixture file.
    """
    file = TOMLFile(Path(__file__).parent / "fixtures" / f"{name}.test")

    if data:
        # if data is provided write it, this is helpful for generating fixtures
        # we expect lock data to be compatible with TOMLDocument for our purposes
        file.write(cast("TOMLDocument", data))

    content: dict[str, Any] = file.read()

    return content


def fix_lock_data(lock_data: dict[str, Any]) -> None:
    if Version.parse(lock_data["metadata"]["lock-version"]) >= Version.parse("2.1"):
        for locked_package in lock_data["package"]:
            locked_package["groups"] = ["main"]
            locked_package["files"] = []
        del lock_data["metadata"]["files"]


def test_run_no_dependencies(installer: Installer, locker: Locker) -> None:
    result = installer.run()
    assert result == 0

    expected = fixture("no-dependencies")
    assert locker.written_data == expected


def test_not_fresh_lock(installer: Installer, locker: Locker) -> None:
    locker.locked().fresh(False)
    with pytest.raises(
        ValueError,
        match=re.escape(
            "pyproject.toml changed significantly since poetry.lock was last generated. "
            "Run `poetry lock` to fix the lock file."
        ),
    ):
        installer.run()


def test_run_with_dependencies(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
) -> None:
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    repo.add_package(package_a)
    repo.add_package(package_b)

    package.add_dependency(Factory.create_dependency("A", "~1.0"))
    package.add_dependency(Factory.create_dependency("B", "^1.0"))

    result = installer.run()
    assert result == 0

    expected = fixture("with-dependencies")
    assert locker.written_data == expected


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
def test_run_update_after_removing_dependencies(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    lock_version: str,
) -> None:
    lock_data = {
        "package": [
            {
                "name": "A",
                "version": "1.0",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
            {
                "name": "B",
                "version": "1.1",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
            {
                "name": "C",
                "version": "1.2",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
            "files": {"A": [], "B": [], "C": []},
        },
    }
    fix_lock_data(lock_data)
    locker.locked(True)
    locker.mock_lock_data(lock_data)
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    package_c = get_package("C", "1.2")
    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    installed.add_package(package_a)
    installed.add_package(package_b)
    installed.add_package(package_c)

    package.add_dependency(Factory.create_dependency("A", "~1.0"))
    package.add_dependency(Factory.create_dependency("B", "~1.1"))

    installer.update(True)
    result = installer.run()
    assert result == 0

    expected = fixture("with-dependencies")
    assert locker.written_data == expected

    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 1


def _configure_run_install_dev(
    lock_version: str,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    with_optional_group: bool = False,
    with_packages_installed: bool = False,
) -> None:
    """
    Perform common test setup for `test_run_install_*dev*()` methods.
    """
    lock_data: dict[str, Any] = {
        "package": [
            {
                "name": "A",
                "version": "1.0",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
            {
                "name": "B",
                "version": "1.1",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
            {
                "name": "C",
                "version": "1.2",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
            "files": {"A": [], "B": [], "C": []},
        },
    }
    if lock_version == "2.1":
        for locked_package in lock_data["package"]:
            locked_package["groups"] = [
                "dev" if locked_package["name"] == "C" else "main"
            ]
            locked_package["files"] = []
        del lock_data["metadata"]["files"]
    locker.locked(True)
    locker.mock_lock_data(lock_data)
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    package_c = get_package("C", "1.2")
    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    if with_packages_installed:
        installed.add_package(package_a)
        installed.add_package(package_b)
        installed.add_package(package_c)

    package.add_dependency(Factory.create_dependency("A", "~1.0"))
    package.add_dependency(Factory.create_dependency("B", "~1.1"))

    group = DependencyGroup("dev", optional=with_optional_group)
    group.add_dependency(Factory.create_dependency("C", "~1.2", groups=["dev"]))
    package.add_dependency_group(group)


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
@pytest.mark.parametrize("update", [False, True])
@pytest.mark.parametrize("requires_synchronization", [False, True])
@pytest.mark.parametrize(
    ("groups", "installs", "updates", "removals", "with_packages_installed"),
    [
        (None, 2, 0, 0, False),
        (None, 0, 0, 1, True),
        ([], 0, 0, 0, False),
        ([], 0, 0, 3, True),
        (["dev"], 1, 0, 0, False),
        (["dev"], 0, 0, 2, True),
        ([MAIN_GROUP], 2, 0, 0, False),
        ([MAIN_GROUP], 0, 0, 1, True),
        ([MAIN_GROUP, "dev"], 3, 0, 0, False),
        ([MAIN_GROUP, "dev"], 0, 0, 0, True),
    ],
)
def test_run_install_with_dependency_groups(
    groups: list[str] | None,
    installs: int,
    updates: int,
    removals: int,
    with_packages_installed: bool,
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    update: bool,
    requires_synchronization: bool,
    lock_version: str,
) -> None:
    _configure_run_install_dev(
        lock_version,
        locker,
        repo,
        package,
        installed,
        with_optional_group=True,
        with_packages_installed=with_packages_installed,
    )

    if groups is not None:
        installer.only_groups({canonicalize_name(g) for g in groups})

    installer.update(update)
    installer.requires_synchronization(requires_synchronization)
    result = installer.run()
    assert result == 0

    if not requires_synchronization:
        removals = 0
    assert installer.executor.installations_count == installs
    assert installer.executor.updates_count == updates
    assert installer.executor.removals_count == removals


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
def test_run_install_does_not_remove_locked_packages_if_installed_but_not_required(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    lock_version: str,
) -> None:
    package_a = get_package("a", "1.0")
    package_b = get_package("b", "1.1")
    package_c = get_package("c", "1.2")

    repo.add_package(package_a)
    installed.add_package(package_a)
    repo.add_package(package_b)
    installed.add_package(package_b)
    repo.add_package(package_c)
    installed.add_package(package_c)

    installed.add_package(package)  # Root package never removed.

    package.add_dependency(
        Factory.create_dependency(package_a.name, str(package_a.version))
    )

    lock_data = {
        "package": [
            {
                "name": package_a.name,
                "version": package_a.version.text,
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
            {
                "name": package_b.name,
                "version": package_b.version.text,
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
            {
                "name": package_c.name,
                "version": package_c.version.text,
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
            "files": {package_a.name: [], package_b.name: [], package_c.name: []},
        },
    }
    fix_lock_data(lock_data)
    locker.locked(True)
    locker.mock_lock_data(lock_data)

    result = installer.run()
    assert result == 0

    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
def test_run_install_removes_locked_packages_if_installed_and_synchronization_is_required(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    lock_version: str,
    config_installer_reresolve: bool,
) -> None:
    package_a = get_package("a", "1.0")
    package_b = get_package("b", "1.1")
    package_c = get_package("c", "1.2")

    repo.add_package(package_a)
    installed.add_package(package_a)
    repo.add_package(package_b)
    installed.add_package(package_b)
    repo.add_package(package_c)
    installed.add_package(package_c)

    installed.add_package(package)  # Root package never removed.

    package.add_dependency(
        Factory.create_dependency(package_a.name, str(package_a.version))
    )

    lock_data = {
        "package": [
            {
                "name": package_a.name,
                "version": package_a.version.text,
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
            {
                "name": package_b.name,
                "version": package_b.version.text,
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
            {
                "name": package_c.name,
                "version": package_c.version.text,
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
            "files": {package_a.name: [], package_b.name: [], package_c.name: []},
        },
    }
    fix_lock_data(lock_data)
    locker.locked(True)
    locker.mock_lock_data(lock_data)

    installer.update(True)
    installer.requires_synchronization(True)
    installer.run()

    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 2


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
def test_run_install_removes_no_longer_locked_packages_if_installed(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    lock_version: str,
) -> None:
    package_a = get_package("a", "1.0")
    package_b = get_package("b", "1.1")
    package_c = get_package("c", "1.2")

    repo.add_package(package_a)
    installed.add_package(package_a)
    repo.add_package(package_b)
    installed.add_package(package_b)
    repo.add_package(package_c)
    installed.add_package(package_c)

    installed.add_package(package)  # Root package never removed.

    package.add_dependency(
        Factory.create_dependency(package_a.name, str(package_a.version))
    )

    lock_data = {
        "package": [
            {
                "name": package_a.name,
                "version": package_a.version.text,
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
            {
                "name": package_b.name,
                "version": package_b.version.text,
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
            {
                "name": package_c.name,
                "version": package_c.version.text,
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
            "files": {package_a.name: [], package_b.name: [], package_c.name: []},
        },
    }
    fix_lock_data(lock_data)
    locker.locked(True)
    locker.mock_lock_data(lock_data)

    installer.update(True)
    result = installer.run()
    assert result == 0

    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 2


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
@pytest.mark.parametrize(
    "managed_reserved_package_names",
    [(), ("pip",)],
)
def test_run_install_with_synchronization(
    managed_reserved_package_names: tuple[str, ...],
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    lock_version: str,
) -> None:
    package_a = get_package("a", "1.0")
    package_b = get_package("b", "1.1")
    package_c = get_package("c", "1.2")
    package_pip = get_package("pip", "20.0.0")

    all_packages = [
        package_a,
        package_b,
        package_c,
        package_pip,
    ]

    managed_reserved_packages = [
        pkg for pkg in all_packages if pkg.name in managed_reserved_package_names
    ]
    locked_packages = [package_a, *managed_reserved_packages]

    for pkg in all_packages:
        repo.add_package(pkg)
        installed.add_package(pkg)

    installed.add_package(package)  # Root package never removed.

    package.add_dependency(
        Factory.create_dependency(package_a.name, str(package_a.version))
    )

    lock_data = {
        "package": [
            {
                "name": pkg.name,
                "version": pkg.version,
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            }
            for pkg in locked_packages
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
            "files": {pkg.name: [] for pkg in locked_packages},
        },
    }
    fix_lock_data(lock_data)
    locker.locked(True)
    locker.mock_lock_data(lock_data)

    installer.update(True)
    installer.requires_synchronization(True)
    result = installer.run()
    assert result == 0

    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 2 + len(managed_reserved_packages)

    expected_removals = {
        package_b.name,
        package_c.name,
        *managed_reserved_package_names,
    }

    assert isinstance(installer.executor, TestExecutor)
    assert {r.name for r in installer.executor.removals} == expected_removals


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
def test_run_whitelist_add(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    lock_version: str,
) -> None:
    lock_data = {
        "package": [
            {
                "name": "A",
                "version": "1.0",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            }
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
            "files": {"A": []},
        },
    }
    fix_lock_data(lock_data)
    locker.locked(True)
    locker.mock_lock_data(lock_data)
    package_a = get_package("A", "1.0")
    package_a_new = get_package("A", "1.1")
    package_b = get_package("B", "1.1")
    repo.add_package(package_a)
    repo.add_package(package_a_new)
    repo.add_package(package_b)

    package.add_dependency(Factory.create_dependency("A", "~1.0"))
    package.add_dependency(Factory.create_dependency("B", "^1.0"))

    installer.update(True)
    installer.whitelist(["B"])

    result = installer.run()
    assert result == 0

    expected = fixture("with-dependencies")
    assert locker.written_data == expected


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
def test_run_whitelist_remove(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    lock_version: str,
) -> None:
    lock_data = {
        "package": [
            {
                "name": "A",
                "version": "1.0",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
            {
                "name": "B",
                "version": "1.1",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
            "files": {"A": [], "B": []},
        },
    }
    fix_lock_data(lock_data)
    locker.locked(True)
    locker.mock_lock_data(lock_data)
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    repo.add_package(package_a)
    repo.add_package(package_b)
    installed.add_package(package_b)

    package.add_dependency(Factory.create_dependency("A", "~1.0"))

    installer.update(True)
    installer.whitelist(["B"])

    result = installer.run()
    assert result == 0

    expected = fixture("remove")
    assert locker.written_data == expected
    assert installer.executor.installations_count == 1
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 1


def test_add_with_sub_dependencies(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
) -> None:
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    package_c = get_package("C", "1.2")
    package_d = get_package("D", "1.3")
    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    package.add_dependency(Factory.create_dependency("A", "~1.0"))
    package.add_dependency(Factory.create_dependency("B", "^1.0"))

    package_a.add_dependency(Factory.create_dependency("D", "^1.0"))
    package_b.add_dependency(Factory.create_dependency("C", "~1.2"))

    result = installer.run()
    assert result == 0

    expected = fixture("with-sub-dependencies")
    assert locker.written_data == expected


def test_run_with_python_versions(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
) -> None:
    package.python_versions = "~2.7 || ^3.4"

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    package_c12 = get_package("C", "1.2")
    package_c12.python_versions = "~2.7 || ^3.3"
    package_c13 = get_package("C", "1.3")
    package_c13.python_versions = "~3.3"

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c12)
    repo.add_package(package_c13)

    package.add_dependency(Factory.create_dependency("A", "~1.0"))
    package.add_dependency(Factory.create_dependency("B", "^1.0"))
    package.add_dependency(Factory.create_dependency("C", "^1.0"))

    result = installer.run()
    assert result == 0

    expected = fixture("with-python-versions")
    assert locker.written_data == expected


def test_run_with_optional_and_python_restricted_dependencies(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
) -> None:
    package.python_versions = "~2.7 || ^3.4"

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    package_c12 = get_package("C", "1.2")
    package_c13 = get_package("C", "1.3")
    package_d = get_package("D", "1.4")
    package_c13.add_dependency(Factory.create_dependency("D", "^1.2"))

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c12)
    repo.add_package(package_c13)
    repo.add_package(package_d)

    package.extras = {canonicalize_name("foo"): [get_dependency("A", "~1.0")]}
    dep_a = Factory.create_dependency("A", {"version": "~1.0", "optional": True})
    dep_a._in_extras = [canonicalize_name("foo")]
    package.add_dependency(dep_a)
    package.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "python": "~2.4"})
    )
    package.add_dependency(
        Factory.create_dependency("C", {"version": "^1.0", "python": "~2.7 || ^3.4"})
    )

    result = installer.run()
    assert result == 0

    expected = fixture("with-optional-dependencies")
    assert locker.written_data == expected

    # We should only have 2 installs:
    # C,D since python version is not compatible
    # with B's python constraint and A is optional
    assert isinstance(installer.executor, TestExecutor)
    assert installer.executor.installations_count == 2
    assert installer.executor.installations[0].name == "d"
    assert installer.executor.installations[1].name == "c"


def test_run_with_optional_and_platform_restricted_dependencies(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    mocker: MockerFixture,
) -> None:
    mocker.patch("sys.platform", "darwin")

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    package_c12 = get_package("C", "1.2")
    package_c13 = get_package("C", "1.3")
    package_d = get_package("D", "1.4")
    package_c13.add_dependency(Factory.create_dependency("D", "^1.2"))

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c12)
    repo.add_package(package_c13)
    repo.add_package(package_d)

    package.extras = {canonicalize_name("foo"): [get_dependency("A", "~1.0")]}
    dep_a = Factory.create_dependency("A", {"version": "~1.0", "optional": True})
    dep_a._in_extras = [canonicalize_name("foo")]
    package.add_dependency(dep_a)
    package.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "platform": "custom"})
    )
    package.add_dependency(
        Factory.create_dependency("C", {"version": "^1.0", "platform": "darwin"})
    )

    result = installer.run()
    assert result == 0

    expected = fixture("with-platform-dependencies")
    assert locker.written_data == expected

    # We should only have 2 installs:
    # C,D since the mocked python version is not compatible
    # with B's python constraint and A is optional
    assert isinstance(installer.executor, TestExecutor)
    assert installer.executor.installations_count == 2
    assert installer.executor.installations[0].name == "d"
    assert installer.executor.installations[1].name == "c"


def test_run_with_dependencies_extras(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
) -> None:
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")

    package_b.extras = {canonicalize_name("foo"): [get_dependency("C", "^1.0")]}
    package_b.add_dependency(
        Factory.create_dependency("C", {"version": "^1.0", "optional": True})
    )

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    package.add_dependency(Factory.create_dependency("A", "^1.0"))
    package.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "extras": ["foo"]})
    )

    result = installer.run()
    assert result == 0

    expected = fixture("with-dependencies-extras")
    assert locker.written_data == expected


def test_run_with_dependencies_nested_extras(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
) -> None:
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")

    dependency_c = Factory.create_dependency("C", {"version": "^1.0", "optional": True})
    dependency_b = Factory.create_dependency(
        "B", {"version": "^1.0", "optional": True, "extras": ["C"]}
    )
    dependency_a = Factory.create_dependency("A", {"version": "^1.0", "extras": ["B"]})

    package_b.extras = {canonicalize_name("c"): [dependency_c]}
    package_b.add_dependency(dependency_c)

    package_a.add_dependency(dependency_b)
    package_a.extras = {canonicalize_name("b"): [dependency_b]}

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    package.add_dependency(dependency_a)

    result = installer.run()
    assert result == 0

    expected = fixture("with-dependencies-nested-extras")
    assert locker.written_data == expected


@pytest.mark.parametrize(
    "enabled_extras",
    [
        ([]),
        (["all"]),
        (["nested"]),
        (["install", "download"]),
        (["install"]),
        (["download"]),
    ],
)
@pytest.mark.parametrize("top_level_dependency", [True, False])
def test_solver_resolves_self_referential_extras(
    enabled_extras: list[str],
    top_level_dependency: bool,
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    create_package: PackageFactory,
) -> None:
    dependency = (
        create_package(
            "A",
            str(package.version),
            extras={
                "download": ["download-package"],
                "install": ["install-package"],
                "py38": ["py38-package ; python_version == '3.8'"],
                "py310": ["py310-package ; python_version > '3.8'"],
                "all": ["a[download,install]"],
                "py": ["a[py38,py310]"],
                "nested": ["a[all]"],
            },
        )
        .to_dependency()
        .with_features(enabled_extras)
    )

    if not top_level_dependency:
        dependency = create_package(
            "B", "1.0", dependencies=[dependency]
        ).to_dependency()

    package.add_dependency(dependency)

    result = installer.run()
    assert result == 0

    name = "-".join(
        [
            "with-self-referencing-extras",
            *enabled_extras,
            "top" if top_level_dependency else "deep",
        ]
    )

    expected = fixture(name)
    assert locker.written_data == expected


def test_solver_resolves_self_referential_extras_with_markers(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    create_package: PackageFactory,
) -> None:
    package.add_dependency(
        Factory.create_dependency("A", {"version": "*", "extras": ["all"]})
    )

    create_package(
        "A",
        str(package.version),
        extras={
            "download": ["download-package"],
            "install": ["install-package"],
            "all": ["a[download,install] ; python_version < '3.9'"],
        },
    )

    result = installer.run()
    assert result == 0

    name = "-".join(["with-self-referencing-extras", "b", "markers"])

    # FIXME: At the time of writing this test case, the markers from self-ref extras are not
    #  correctly propagated into the dependency specs. For example, given this case,
    #  the package "install-package" should have a final marker of
    #  "extra == 'install' or extra == 'all' and python_version < '3.9'".
    expected = fixture(name)
    assert locker.written_data == expected


@pytest.mark.parametrize("root", [True, False])
@pytest.mark.parametrize("locked", [False, True])
@pytest.mark.parametrize("extra", [None, "extra-one", "extra-two"])
def test_run_with_conflicting_dependency_extras(
    installer: Installer,
    pool: RepositoryPool,
    locker: Locker,
    installed: CustomInstalledRepository,
    repo: Repository,
    config: Config,
    package: ProjectPackage,
    extra: str | None,
    locked: bool,
    root: bool,
) -> None:
    """
    - https://github.com/python-poetry/poetry/issues/6419

    Tests resolution of extras with conflicting dependencies. Tests in both as direct dependencies of
    root package and as transitive dependencies.
    """
    # A package with two optional dependencies, one for each extra
    # If root, this is the root package, otherwise an intermediate package
    main_package = package if root else get_package("intermediate-dep", "1.0.0")

    # Two conflicting versions of a dependency, one in each extra
    conflicting_dep_one_pkg = get_package("conflicting-dep", "1.1.0")
    conflicting_dep_two_pkg = get_package("conflicting-dep", "1.2.0")

    conflicting_dep_one = Factory.create_dependency(
        "conflicting-dep",
        {
            "version": "1.1.0",
            "markers": "extra == 'extra-one' and extra != 'extra-two'",
            "optional": True,
        },
    )
    conflicting_dep_two = Factory.create_dependency(
        "conflicting-dep",
        {
            "version": "1.2.0",
            "markers": "extra != 'extra-one' and extra == 'extra-two'",
            "optional": True,
        },
    )

    # Include both just for extra validation that our marker validation works as expected
    main_package.extras = {
        canonicalize_name("extra-one"): [conflicting_dep_one, conflicting_dep_two],
        canonicalize_name("extra-two"): [conflicting_dep_one, conflicting_dep_two],
    }
    main_package.add_dependency(conflicting_dep_one)
    main_package.add_dependency(conflicting_dep_two)

    repo.add_package(conflicting_dep_one_pkg)
    repo.add_package(conflicting_dep_two_pkg)
    if not root:
        repo.add_package(main_package)

    # If we have an intermediate package, add extras to our root package
    if not root:
        extra_one_dep = Factory.create_dependency(
            "intermediate-dep",
            {
                "version": "1.0.0",
                "markers": "extra == 'root-extra-one' and extra != 'root-extra-two'",
                "extras": ["extra-one"],
                "optional": True,
            },
        )
        extra_two_dep = Factory.create_dependency(
            "intermediate-dep",
            {
                "version": "1.0.0",
                "markers": "extra != 'root-extra-one' and extra == 'root-extra-two'",
                "extras": ["extra-two"],
                "optional": True,
            },
        )
        package.add_dependency(extra_one_dep)
        package.add_dependency(extra_two_dep)
        # Include both just for extra validation that our marker validation works as expected
        package.extras = {
            canonicalize_name("root-extra-one"): [extra_one_dep, extra_two_dep],
            canonicalize_name("root-extra-two"): [extra_one_dep, extra_two_dep],
        }

    fixture_name = "with-conflicting-dependency-extras-" + (
        "root" if root else "transitive"
    )
    locker.locked(locked)
    if locked:
        locker.mock_lock_data(dict(fixture(fixture_name)))

    if extra is not None:
        extras = [f"root-{extra}"] if not root else [extra]
        installer.extras(extras)
    result = installer.run()
    assert result == 0

    if not locked:
        expected = fixture(fixture_name)
        assert locker.written_data == expected

    # Results of installation are consistent with the 'extra' input
    assert isinstance(installer.executor, TestExecutor)

    expected_installations = []
    if extra == "extra-one":
        expected_installations.append(conflicting_dep_one_pkg)
    elif extra == "extra-two":
        expected_installations.append(conflicting_dep_two_pkg)
    if not root and extra is not None:
        expected_installations.append(get_package("intermediate-dep", "1.0.0"))

    assert len(installer.executor.installations) == len(expected_installations)
    assert set(installer.executor.installations) == set(expected_installations)


@pytest.mark.parametrize("locked", [True, False])
@pytest.mark.parametrize("extra", [None, "cpu", "cuda"])
def test_run_with_exclusive_extras_different_sources(
    installer: Installer,
    locker: Locker,
    installed: CustomInstalledRepository,
    config: Config,
    package: ProjectPackage,
    extra: str | None,
    locked: bool,
) -> None:
    """
    - https://github.com/python-poetry/poetry/issues/6409
    - https://github.com/python-poetry/poetry/issues/6419
    - https://github.com/python-poetry/poetry/issues/7748
    - https://github.com/python-poetry/poetry/issues/9537
    """
    # Setup repo for each of our sources
    cpu_repo = Repository("pytorch-cpu")
    cuda_repo = Repository("pytorch-cuda")
    pool = RepositoryPool()
    pool.add_repository(cpu_repo)
    pool.add_repository(cuda_repo)
    config.config["repositories"] = {
        "pytorch-cpu": {"url": "https://download.pytorch.org/whl/cpu"},
        "pytorch-cuda": {"url": "https://download.pytorch.org/whl/cuda"},
    }

    # Configure packages that read from each of the different sources
    torch_cpu_pkg = get_package("torch", "1.11.0+cpu")
    torch_cpu_pkg._source_reference = "pytorch-cpu"
    torch_cpu_pkg._source_type = "legacy"
    torch_cpu_pkg._source_url = "https://download.pytorch.org/whl/cpu"
    torch_cuda_pkg = get_package("torch", "1.11.0+cuda")
    torch_cuda_pkg._source_reference = "pytorch-cuda"
    torch_cuda_pkg._source_type = "legacy"
    torch_cuda_pkg._source_url = "https://download.pytorch.org/whl/cuda"
    cpu_repo.add_package(torch_cpu_pkg)
    cuda_repo.add_package(torch_cuda_pkg)

    # Depend on each package based on exclusive extras
    torch_cpu_dep = Factory.create_dependency(
        "torch",
        {
            "version": "1.11.0+cpu",
            "markers": "extra == 'cpu' and extra != 'cuda'",
            "source": "pytorch-cpu",
        },
    )
    torch_cuda_dep = Factory.create_dependency(
        "torch",
        {
            "version": "1.11.0+cuda",
            "markers": "extra != 'cpu' and extra == 'cuda'",
            "source": "pytorch-cuda",
        },
    )
    package.add_dependency(torch_cpu_dep)
    package.add_dependency(torch_cuda_dep)
    # We don't want to cheat by only including the correct dependency in the 'extra' mapping
    package.extras = {
        canonicalize_name("cpu"): [torch_cpu_dep, torch_cuda_dep],
        canonicalize_name("cuda"): [torch_cpu_dep, torch_cuda_dep],
    }

    # Set locker state
    locker.locked(locked)
    if locked:
        locker.mock_lock_data(dict(fixture("with-exclusive-extras")))

    # Perform install
    installer = Installer(
        NullIO(),
        MockEnv(),
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=TestExecutor(
            MockEnv(),
            pool,
            config,
            NullIO(),
        ),
    )
    if extra is not None:
        installer.extras([extra])
    result = installer.run()
    assert result == 0

    # Results of locking are expected and installation are consistent with the 'extra' input
    if not locked:
        expected = fixture("with-exclusive-extras")
        assert locker.written_data == expected
    assert isinstance(installer.executor, TestExecutor)
    if extra is None:
        assert len(installer.executor.installations) == 0
    else:
        assert len(installer.executor.installations) == 1
        version = f"1.11.0+{extra}"
        source_url = f"https://download.pytorch.org/whl/{extra}"
        source_reference = f"pytorch-{extra}"
        assert installer.executor.installations[0] == Package(
            "torch",
            version,
            source_type="legacy",
            source_url=source_url,
            source_reference=source_reference,
        )


@pytest.mark.parametrize("locked", [True, False])
@pytest.mark.parametrize("extra", [None, "extra-one", "extra-two"])
def test_run_with_different_dependency_extras(
    installer: Installer,
    pool: RepositoryPool,
    locker: Locker,
    installed: CustomInstalledRepository,
    repo: Repository,
    config: Config,
    package: ProjectPackage,
    extra: str | None,
    locked: bool,
) -> None:
    """
    - https://github.com/python-poetry/poetry/issues/834
    - https://github.com/python-poetry/poetry/issues/7748

    This tests different sets of extras in a dependency of the root project. These different dependency extras are
    themselves conditioned on extras in the root project.
    """
    # Three packages in addition to root: demo (direct dependency) and two transitive dep packages
    demo_pkg = get_package("demo", "1.0.0")
    transitive_one_pkg = get_package("transitive-dep-one", "1.1.0")
    transitive_two_pkg = get_package("transitive-dep-two", "1.2.0")

    # Switch each transitive dependency based on extra markers in the 'demo' package
    transitive_dep_one = Factory.create_dependency(
        "transitive-dep-one",
        {
            "version": "1.1.0",
            "markers": "extra == 'demo-extra-one' and extra != 'demo-extra-two'",
            "optional": True,
        },
    )
    transitive_dep_two = Factory.create_dependency(
        "transitive-dep-two",
        {
            "version": "1.2.0",
            "markers": "extra != 'demo-extra-one' and extra == 'demo-extra-two'",
            "optional": True,
        },
    )
    # Include both packages in both demo extras, to validate that they're filtered out based on extra markers alone
    demo_pkg.extras = {
        canonicalize_name("demo-extra-one"): [
            get_dependency("transitive-dep-one"),
            get_dependency("transitive-dep-two"),
        ],
        canonicalize_name("demo-extra-two"): [
            get_dependency("transitive-dep-one"),
            get_dependency("transitive-dep-two"),
        ],
    }
    demo_pkg.add_dependency(transitive_dep_one)
    demo_pkg.add_dependency(transitive_dep_two)

    # Now define the demo dependency, similarly switched on extra markers in the root package
    extra_one_dep = Factory.create_dependency(
        "demo",
        {
            "version": "1.0.0",
            "markers": "extra == 'extra-one' and extra != 'extra-two'",
            "extras": ["demo-extra-one"],
        },
    )
    extra_two_dep = Factory.create_dependency(
        "demo",
        {
            "version": "1.0.0",
            "markers": "extra != 'extra-one' and extra == 'extra-two'",
            "extras": ["demo-extra-two"],
        },
    )
    package.add_dependency(extra_one_dep)
    package.add_dependency(extra_two_dep)
    # Again we don't want to cheat by only including the correct dependency in the 'extra' mapping
    package.extras = {
        canonicalize_name("extra-one"): [extra_one_dep, extra_two_dep],
        canonicalize_name("extra-two"): [extra_one_dep, extra_two_dep],
    }

    repo.add_package(demo_pkg)
    repo.add_package(transitive_one_pkg)
    repo.add_package(transitive_two_pkg)

    locker.locked(locked)
    if locked:
        locker.mock_lock_data(dict(fixture("with-dependencies-differing-extras")))

    installer = Installer(
        NullIO(),
        MockEnv(),
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=TestExecutor(
            MockEnv(),
            pool,
            config,
            NullIO(),
        ),
    )
    if extra is not None:
        installer.extras([extra])
    result = installer.run()
    assert result == 0

    if not locked:
        expected = fixture("with-dependencies-differing-extras")
        assert locker.written_data == expected

    # Results of installation are consistent with the 'extra' input
    assert isinstance(installer.executor, TestExecutor)
    if extra is None:
        assert len(installer.executor.installations) == 0
    else:
        assert len(installer.executor.installations) == 2


@pytest.mark.parametrize("is_locked", [False, True])
@pytest.mark.parametrize("is_installed", [False, True])
@pytest.mark.parametrize("with_extras", [False, True])
@pytest.mark.parametrize("do_update", [False, True])
@pytest.mark.parametrize("do_sync", [False, True])
def test_run_installs_extras_with_deps_if_requested(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    installed: CustomInstalledRepository,
    package: ProjectPackage,
    is_locked: bool,
    is_installed: bool,
    with_extras: bool,
    do_update: bool,
    do_sync: bool,
) -> None:
    package.extras = {canonicalize_name("foo"): [get_dependency("C")]}
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_d = get_package("D", "1.1")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    package.add_dependency(Factory.create_dependency("A", "^1.0"))
    package.add_dependency(Factory.create_dependency("B", "^1.0"))
    dep_c = Factory.create_dependency("C", {"version": "^1.0", "optional": True})
    dep_c._in_extras = [canonicalize_name("foo")]
    package.add_dependency(dep_c)

    package_c.add_dependency(Factory.create_dependency("D", "^1.0"))

    if is_locked:
        locker.locked(True)
        locker.mock_lock_data(fixture("extras-with-dependencies"))

    if is_installed:
        installed.add_package(package_a)
        installed.add_package(package_b)
        installed.add_package(package_c)
        installed.add_package(package_d)

    if with_extras:
        installer.extras(["foo"])
    installer.update(do_update)
    installer.requires_synchronization(do_sync)
    result = installer.run()
    assert result == 0

    if not is_locked:
        assert locker.written_data == fixture("extras-with-dependencies")

    if with_extras:
        # A, B, C, D
        expected_installations_count = 0 if is_installed else 4
        expected_removals_count = 0
    else:
        # A, B
        expected_installations_count = 0 if is_installed else 2
        # We only want to uninstall extras if we do a "poetry install" without extras,
        # not if we do a "poetry update" or "poetry add".
        expected_removals_count = 2 if is_installed and do_sync else 0

    assert installer.executor.installations_count == expected_installations_count
    assert installer.executor.removals_count == expected_removals_count


def test_installer_with_pypi_repository(
    package: ProjectPackage,
    locker: Locker,
    installed: CustomInstalledRepository,
    config: Config,
    env: NullEnv,
    pypi_repository: PyPiRepository,
) -> None:
    pool = RepositoryPool()
    pool.add_repository(pypi_repository)

    installer = Installer(
        NullIO(), env, package, locker, pool, config, installed=installed
    )

    package.python_versions = ">=3.7"
    package.add_dependency(Factory.create_dependency("pytest", "^3.5", groups=["dev"]))
    result = installer.run()
    assert result == 0

    expected = fixture("with-pypi-repository")
    assert locker.written_data == expected


def test_run_installs_with_local_file(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: FixtureDirGetter,
) -> None:
    root_dir = Path(__file__).parent.parent.parent
    package.root_dir = root_dir
    locker.set_lock_path(root_dir)
    file_path = fixture_dir("distributions/demo-0.1.0-py2.py3-none-any.whl")
    package.add_dependency(
        Factory.create_dependency(
            "demo", {"file": str(file_path.relative_to(root_dir))}, root_dir=root_dir
        )
    )

    repo.add_package(get_package("pendulum", "1.4.4"))

    result = installer.run()
    assert result == 0

    expected = fixture("with-file-dependency")

    assert locker.written_data == expected
    assert installer.executor.installations_count == 2


def test_run_installs_wheel_with_no_requires_dist(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: FixtureDirGetter,
) -> None:
    root_dir = Path(__file__).parent.parent.parent
    package.root_dir = root_dir
    locker.set_lock_path(root_dir)
    file_path = fixture_dir(
        "wheel_with_no_requires_dist/demo-0.1.0-py2.py3-none-any.whl"
    )
    package.add_dependency(
        Factory.create_dependency(
            "demo", {"file": str(file_path.relative_to(root_dir))}, root_dir=root_dir
        )
    )

    result = installer.run()
    assert result == 0

    expected = fixture("with-wheel-dependency-no-requires-dist")

    assert locker.written_data == expected

    assert installer.executor.installations_count == 1


def test_run_installs_with_local_poetry_directory_and_extras(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    tmpdir: Path,
    fixture_dir: FixtureDirGetter,
) -> None:
    root_dir = Path(__file__).parent.parent.parent
    package.root_dir = root_dir
    locker.set_lock_path(root_dir)
    file_path = fixture_dir("project_with_extras")
    package.add_dependency(
        Factory.create_dependency(
            "project-with-extras",
            {"path": str(file_path.relative_to(root_dir)), "extras": ["extras_a"]},
            root_dir=root_dir,
        )
    )

    repo.add_package(get_package("pendulum", "1.4.4"))

    result = installer.run()
    assert result == 0

    expected = fixture("with-directory-dependency-poetry")
    assert locker.written_data == expected

    assert installer.executor.installations_count == 2


@pytest.mark.parametrize("skip_directory", [True, False])
def test_run_installs_with_local_poetry_directory_and_skip_directory_flag(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: FixtureDirGetter,
    skip_directory: bool,
) -> None:
    """When we set Installer.skip_directory(True) no path dependencies should
    be installed (including transitive dependencies).
    """
    root_dir = fixture_dir("directory")
    package.root_dir = root_dir
    locker.set_lock_path(root_dir)
    directory = root_dir.joinpath("project_with_transitive_directory_dependencies")
    package.add_dependency(
        Factory.create_dependency(
            "project-with-transitive-directory-dependencies",
            {"path": str(directory.relative_to(root_dir))},
            root_dir=root_dir,
        )
    )

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cachy", "0.2.0"))

    installer.skip_directory(skip_directory)

    result = installer.run()
    assert result == 0

    expected = fixture("with-directory-dependency-poetry-transitive")

    assert locker.written_data == expected

    assert isinstance(installer.executor, TestExecutor)
    directory_installs = [
        p.name for p in installer.executor.installations if p.source_type == "directory"
    ]

    if skip_directory:
        assert not directory_installs, directory_installs
        assert installer.executor.installations_count == 2
    else:
        assert directory_installs, directory_installs
        assert installer.executor.installations_count == 6


def test_run_installs_with_local_poetry_file_transitive(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    tmpdir: str,
    fixture_dir: FixtureDirGetter,
) -> None:
    root_dir = fixture_dir("directory")
    package.root_dir = root_dir
    locker.set_lock_path(root_dir)
    directory = fixture_dir("directory").joinpath(
        "project_with_transitive_file_dependencies"
    )
    package.add_dependency(
        Factory.create_dependency(
            "project-with-transitive-file-dependencies",
            {"path": str(directory.relative_to(root_dir))},
            root_dir=root_dir,
        )
    )

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cachy", "0.2.0"))

    result = installer.run()
    assert result == 0

    expected = fixture("with-file-dependency-transitive")

    assert locker.written_data == expected

    assert installer.executor.installations_count == 4


def test_run_installs_with_local_setuptools_directory(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    tmp_path: Path,
    fixture_dir: FixtureDirGetter,
) -> None:
    root_dir = tmp_path / "root"
    package.root_dir = root_dir
    locker.set_lock_path(root_dir)
    file_path = shutil.copytree(fixture_dir("project_with_setup"), root_dir / "project")
    package.add_dependency(
        Factory.create_dependency(
            "project-with-setup",
            {"path": str(file_path.relative_to(root_dir))},
            root_dir=root_dir,
        )
    )

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cachy", "0.2.0"))

    result = installer.run()
    assert result == 0

    expected = fixture("with-directory-dependency-setuptools")

    assert locker.written_data == expected
    assert installer.executor.installations_count == 3


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
def test_run_with_prereleases(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    lock_version: str,
) -> None:
    lock_data = {
        "package": [
            {
                "name": "A",
                "version": "1.0a2",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            }
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
            "files": {"A": []},
        },
    }
    fix_lock_data(lock_data)
    locker.locked(True)
    locker.mock_lock_data(lock_data)
    package_a = get_package("A", "1.0a2")
    package_b = get_package("B", "1.1")
    repo.add_package(package_a)
    repo.add_package(package_b)

    package.add_dependency(
        Factory.create_dependency("A", {"version": "*", "allow-prereleases": True})
    )
    package.add_dependency(Factory.create_dependency("B", "^1.1"))

    installer.update(True)
    installer.whitelist({"B": "^1.1"})

    result = installer.run()
    assert result == 0

    expected = fixture("with-prereleases")
    assert locker.written_data == expected


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
def test_run_update_all_with_lock(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    lock_version: str,
) -> None:
    lock_data = {
        "package": [
            {
                "name": "A",
                "version": "1.0",
                "optional": True,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            }
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
            "files": {"A": []},
        },
    }
    fix_lock_data(lock_data)
    locker.locked(True)
    locker.mock_lock_data(lock_data)
    package_a = get_package("A", "1.1")
    repo.add_package(get_package("A", "1.0"))
    repo.add_package(package_a)

    package.add_dependency(Factory.create_dependency("A", "*"))

    installer.update(True)

    result = installer.run()
    assert result == 0

    expected = fixture("update-with-lock")
    assert locker.written_data == expected


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
def test_run_update_with_locked_extras(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    lock_version: str,
) -> None:
    lock_data = {
        "package": [
            {
                "name": "A",
                "version": "1.0",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
                "dependencies": {"B": "^1.0", "C": "^1.0"},
            },
            {
                "name": "B",
                "version": "1.0",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
            {
                "name": "C",
                "version": "1.1",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
                "requirements": {"python": "~2.7"},
            },
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
            "files": {"A": [], "B": [], "C": []},
        },
    }
    fix_lock_data(lock_data)
    locker.locked(True)
    locker.mock_lock_data(lock_data)
    package_a = get_package("A", "1.0")
    package_a.extras = {canonicalize_name("foo"): [get_dependency("B")]}
    b_dependency = get_dependency("B", "^1.0", optional=True)
    b_dependency._in_extras = [canonicalize_name("foo")]
    c_dependency = get_dependency("C", "^1.0")
    c_dependency.python_versions = "~2.7"
    package_a.add_dependency(b_dependency)
    package_a.add_dependency(c_dependency)

    repo.add_package(package_a)
    repo.add_package(get_package("B", "1.0"))
    repo.add_package(get_package("C", "1.1"))
    repo.add_package(get_package("D", "1.1"))

    package.add_dependency(
        Factory.create_dependency("A", {"version": "^1.0", "extras": ["foo"]})
    )
    package.add_dependency(Factory.create_dependency("D", "^1.0"))

    installer.update(True)
    installer.whitelist("D")

    result = installer.run()
    assert result == 0

    expected = fixture("update-with-locked-extras")
    assert locker.written_data == expected


def test_run_install_duplicate_dependencies_different_constraints(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
) -> None:
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "python": "<4.0"})
    )
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^2.0", "python": ">=4.0"})
    )

    package_b10 = get_package("B", "1.0")
    package_b20 = get_package("B", "2.0")
    package_b10.add_dependency(Factory.create_dependency("C", "1.2"))
    package_b20.add_dependency(Factory.create_dependency("C", "1.5"))

    package_c12 = get_package("C", "1.2")
    package_c15 = get_package("C", "1.5")

    repo.add_package(package_a)
    repo.add_package(package_b10)
    repo.add_package(package_b20)
    repo.add_package(package_c12)
    repo.add_package(package_c15)

    result = installer.run()
    assert result == 0

    expected = fixture("with-duplicate-dependencies")

    assert locker.written_data == expected

    assert isinstance(installer.executor, TestExecutor)
    installs = installer.executor.installations
    assert installer.executor.installations_count == 3
    assert installs[0] == package_c12
    assert installs[1] == package_b10
    assert installs[2] == package_a

    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
def test_run_install_duplicate_dependencies_different_constraints_with_lock(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    lock_version: str,
) -> None:
    lock_data = {
        "package": [
            {
                "name": "A",
                "version": "1.0",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
                "dependencies": {
                    "B": [
                        {"version": "^1.0", "python": "<4.0"},
                        {"version": "^2.0", "python": ">=4.0"},
                    ]
                },
            },
            {
                "name": "B",
                "version": "1.0",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
                "dependencies": {"C": "1.2"},
                "requirements": {"python": "<4.0"},
            },
            {
                "name": "B",
                "version": "2.0",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
                "dependencies": {"C": "1.5"},
                "requirements": {"python": ">=4.0"},
            },
            {
                "name": "C",
                "version": "1.2",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
            {
                "name": "C",
                "version": "1.5",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
            "files": {"A": [], "B": [], "C": []},
        },
    }
    fix_lock_data(lock_data)
    locker.locked(True)
    locker.mock_lock_data(lock_data)

    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "python": "<4.0"})
    )
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^2.0", "python": ">=4.0"})
    )

    package_b10 = get_package("B", "1.0")
    package_b20 = get_package("B", "2.0")
    package_b10.add_dependency(Factory.create_dependency("C", "1.2"))
    package_b20.add_dependency(Factory.create_dependency("C", "1.5"))

    package_c12 = get_package("C", "1.2")
    package_c15 = get_package("C", "1.5")

    repo.add_package(package_a)
    repo.add_package(package_b10)
    repo.add_package(package_b20)
    repo.add_package(package_c12)
    repo.add_package(package_c15)

    installer.update(True)
    result = installer.run()
    assert result == 0

    expected = fixture("with-duplicate-dependencies")

    assert locker.written_data == expected

    assert installer.executor.installations_count == 3
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
def test_run_update_uninstalls_after_removal_transitive_dependency(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    lock_version: str,
) -> None:
    lock_data = {
        "package": [
            {
                "name": "A",
                "version": "1.0",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
                "dependencies": {"B": {"version": "^1.0", "python": "<2.0"}},
            },
            {
                "name": "B",
                "version": "1.0",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
            "files": {"A": [], "B": []},
        },
    }
    fix_lock_data(lock_data)
    locker.locked(True)
    locker.mock_lock_data(lock_data)
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.0")
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "python": "<2.0"})
    )

    package_b10 = get_package("B", "1.0")

    repo.add_package(package_a)
    repo.add_package(package_b10)

    installed.add_package(get_package("A", "1.0"))
    installed.add_package(get_package("B", "1.0"))

    installer.update(True)
    result = installer.run()
    assert result == 0

    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 1


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
def test_run_install_duplicate_dependencies_different_constraints_with_lock_update(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    lock_version: str,
) -> None:
    lock_data = {
        "package": [
            {
                "name": "A",
                "version": "1.0",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
                "dependencies": {
                    "B": [
                        {"version": "^1.0", "python": "<2.7"},
                        {"version": "^2.0", "python": ">=2.7"},
                    ]
                },
            },
            {
                "name": "B",
                "version": "1.0",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
                "dependencies": {"C": "1.2"},
                "requirements": {"python": "<2.7"},
            },
            {
                "name": "B",
                "version": "2.0",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
                "dependencies": {"C": "1.5"},
                "requirements": {"python": ">=2.7"},
            },
            {
                "name": "C",
                "version": "1.2",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
            {
                "name": "C",
                "version": "1.5",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
            },
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
            "files": {"A": [], "B": [], "C": []},
        },
    }
    fix_lock_data(lock_data)
    locker.locked(True)
    locker.mock_lock_data(lock_data)
    package.add_dependency(Factory.create_dependency("A", "*"))

    package_a = get_package("A", "1.1")
    package_a.add_dependency(Factory.create_dependency("B", "^2.0"))

    package_b10 = get_package("B", "1.0")
    package_b20 = get_package("B", "2.0")
    package_b10.add_dependency(Factory.create_dependency("C", "1.2"))
    package_b20.add_dependency(Factory.create_dependency("C", "1.5"))

    package_c12 = get_package("C", "1.2")
    package_c15 = get_package("C", "1.5")

    repo.add_package(package_a)
    repo.add_package(package_b10)
    repo.add_package(package_b20)
    repo.add_package(package_c12)
    repo.add_package(package_c15)

    installed.add_package(get_package("A", "1.0"))

    installer.update(True)
    installer.whitelist(["A"])
    result = installer.run()
    assert result == 0

    expected = fixture("with-duplicate-dependencies-update")

    assert locker.written_data == expected

    assert installer.executor.installations_count == 2
    assert installer.executor.updates_count == 1
    assert installer.executor.removals_count == 0


def test_installer_test_solver_finds_compatible_package_for_dependency_python_not_fully_compatible_with_package_python(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
) -> None:
    package.python_versions = "~2.7 || ^3.4"
    package.add_dependency(
        Factory.create_dependency("A", {"version": "^1.0", "python": "^3.5"})
    )

    package_a101 = get_package("A", "1.0.1")
    package_a101.python_versions = ">=3.6"

    package_a100 = get_package("A", "1.0.0")
    package_a100.python_versions = ">=3.5"

    repo.add_package(package_a100)
    repo.add_package(package_a101)

    result = installer.run()
    assert result == 0

    expected = fixture("with-conditional-dependency")
    assert locker.written_data == expected
    assert installer.executor.installations_count == 1


def test_installer_required_extras_should_not_be_removed_when_updating_single_dependency(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    env: NullEnv,
    pool: RepositoryPool,
    config: Config,
) -> None:
    package.add_dependency(Factory.create_dependency("A", {"version": "^1.0"}))

    package_a = get_package("A", "1.0.0")
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "extras": ["foo"]})
    )

    package_b = get_package("B", "1.0.0")
    package_b.add_dependency(
        Factory.create_dependency("C", {"version": "^1.0", "optional": True})
    )
    package_b.extras = {canonicalize_name("foo"): [get_dependency("C")]}

    package_c = get_package("C", "1.0.0")
    package_d = get_package("D", "1.0.0")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    installer.update(True)
    result = installer.run()
    assert result == 0

    assert installer.executor.installations_count == 3
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0

    package.add_dependency(Factory.create_dependency("D", "^1.0"))
    locker.locked(True)
    locker.mock_lock_data(locker.written_data)

    installed.add_package(package_a)
    installed.add_package(package_b)
    installed.add_package(package_c)

    installer = Installer(
        NullIO(),
        env,
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=TestExecutor(env, pool, config, NullIO()),
    )
    installer.update(True)
    installer.whitelist(["D"])
    result = installer.run()
    assert result == 0

    assert installer.executor.installations_count == 1
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_installer_required_extras_should_not_be_removed_when_updating_single_dependency_pypi_repository(
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    env: NullEnv,
    mocker: MockerFixture,
    config: Config,
    pypi_repository: PyPiRepository,
) -> None:
    mocker.patch("sys.platform", "darwin")

    pool = RepositoryPool()
    pool.add_repository(pypi_repository)

    installer = Installer(
        NullIO(),
        env,
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=TestExecutor(env, pool, config, NullIO()),
    )

    package.add_dependency(
        Factory.create_dependency(
            "with-transitive-extra-dependency", {"version": "^0.12"}
        )
    )

    installer.update(True)
    result = installer.run()
    assert result == 0

    assert installer.executor.installations_count == 3
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0

    package.add_dependency(Factory.create_dependency("pytest", "^3.5"))

    locker.locked(True)
    locker.mock_lock_data(locker.written_data)

    assert isinstance(installer.executor, TestExecutor)
    for pkg in installer.executor.installations:
        installed.add_package(pkg)

    installer = Installer(
        NullIO(),
        env,
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=TestExecutor(env, pool, config, NullIO()),
    )
    installer.update(True)
    installer.whitelist(["pytest"])
    result = installer.run()
    assert result == 0

    assert installer.executor.installations_count == 7
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_installer_required_extras_should_be_installed(
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    env: NullEnv,
    config: Config,
    pypi_repository: PyPiRepository,
) -> None:
    pool = RepositoryPool()
    pool.add_repository(pypi_repository)

    installer = Installer(
        NullIO(),
        env,
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=TestExecutor(env, pool, config, NullIO()),
    )
    package.add_dependency(
        Factory.create_dependency(
            "with-extra-dependency", {"version": "^0.12", "extras": ["filecache"]}
        )
    )

    installer.update(True)
    result = installer.run()
    assert result == 0

    assert installer.executor.installations_count == 2
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0

    locker.locked(True)
    locker.mock_lock_data(locker.written_data)

    installer = Installer(
        NullIO(),
        env,
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=TestExecutor(env, pool, config, NullIO()),
    )
    installer.update(True)
    result = installer.run()
    assert result == 0

    assert installer.executor.installations_count == 2
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
def test_update_multiple_times_with_split_dependencies_is_idempotent(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    lock_version: str,
) -> None:
    lock_data = {
        "package": [
            {
                "name": "A",
                "version": "1.0",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
                "dependencies": {"B": ">=1.0"},
            },
            {
                "name": "B",
                "version": "1.0.1",
                "optional": False,
                "platform": "*",
                "python-versions": ">=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*",
                "checksum": [],
                "dependencies": {},
            },
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
            "files": {"A": [], "B": []},
        },
    }
    fix_lock_data(lock_data)
    locker.locked(True)
    locker.mock_lock_data(lock_data)

    package.python_versions = "~2.7 || ^3.4"
    package.add_dependency(Factory.create_dependency("A", "^1.0"))

    a10 = get_package("A", "1.0")
    a11 = get_package("A", "1.1")
    a11.add_dependency(Factory.create_dependency("B", ">=1.0.1"))
    a11.add_dependency(
        Factory.create_dependency("C", {"version": "^1.0", "python": "~2.7"})
    )
    a11.add_dependency(
        Factory.create_dependency("C", {"version": "^2.0", "python": "^3.4"})
    )
    b101 = get_package("B", "1.0.1")
    b110 = get_package("B", "1.1.0")
    repo.add_package(a10)
    repo.add_package(a11)
    repo.add_package(b101)
    repo.add_package(b110)
    repo.add_package(get_package("C", "1.0"))
    repo.add_package(get_package("C", "2.0"))
    expected = fixture("with-multiple-updates")

    installer.update(True)
    result = installer.run()
    assert result == 0

    assert locker.written_data == expected

    locker.mock_lock_data(locker.written_data)

    installer.update(True)
    result = installer.run()
    assert result == 0

    assert locker.written_data == expected

    locker.mock_lock_data(locker.written_data)

    installer.update(True)
    result = installer.run()
    assert result == 0

    assert locker.written_data == expected


def test_installer_can_install_dependencies_from_forced_source(
    locker: Locker,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    env: NullEnv,
    config: Config,
    legacy_repository: LegacyRepository,
    pypi_repository: PyPiRepository,
) -> None:
    package.python_versions = "^3.7"
    package.add_dependency(
        Factory.create_dependency("tomlkit", {"version": "^0.5", "source": "legacy"})
    )

    pool = RepositoryPool()
    pool.add_repository(legacy_repository)
    pool.add_repository(pypi_repository)

    installer = Installer(
        NullIO(),
        env,
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=TestExecutor(env, pool, config, NullIO()),
    )
    installer.update(True)
    result = installer.run()
    assert result == 0

    assert installer.executor.installations_count == 1
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_run_installs_with_url_file(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
) -> None:
    url = "https://files.pythonhosted.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
    package.add_dependency(Factory.create_dependency("demo", {"url": url}))

    repo.add_package(get_package("pendulum", "1.4.4"))

    result = installer.run()
    assert result == 0

    expected = fixture("with-url-dependency")

    assert locker.written_data == expected

    assert installer.executor.installations_count == 2


@pytest.mark.parametrize("env_platform", ["linux", "win32"])
def test_run_installs_with_same_version_url_files(
    pool: RepositoryPool,
    locker: Locker,
    installed: CustomInstalledRepository,
    config: Config,
    repo: Repository,
    package: ProjectPackage,
    env_platform: str,
) -> None:
    urls = {
        "linux": "https://files.pythonhosted.org/distributions/demo-0.1.0.tar.gz",
        "win32": (
            "https://files.pythonhosted.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
        ),
    }
    for platform, url in urls.items():
        package.add_dependency(
            Factory.create_dependency(
                "demo",
                {"url": url, "markers": f"sys_platform == '{platform}'"},
            )
        )
    repo.add_package(get_package("pendulum", "1.4.4"))

    installer = Installer(
        NullIO(),
        MockEnv(platform=env_platform),
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=TestExecutor(
            MockEnv(platform=env_platform),
            pool,
            config,
            NullIO(),
        ),
    )
    result = installer.run()
    assert result == 0

    expected = fixture("with-same-version-url-dependencies")
    assert locker.written_data == expected
    assert isinstance(installer.executor, TestExecutor)
    assert installer.executor.installations_count == 2
    demo_package = next(p for p in installer.executor.installations if p.name == "demo")
    assert demo_package.source_url == urls[env_platform]


def test_installer_uses_prereleases_if_they_are_compatible(
    installer: Installer, locker: Locker, package: ProjectPackage, repo: Repository
) -> None:
    package.python_versions = "~2.7 || ^3.4"
    package.add_dependency(
        Factory.create_dependency(
            "prerelease", {"git": "https://github.com/demo/prerelease.git"}
        )
    )

    package_b = get_package("b", "2.0.0")
    package_b.add_dependency(Factory.create_dependency("prerelease", ">=0.19"))

    repo.add_package(package_b)

    result = installer.run()
    assert result == 0

    locker.locked(True)
    locker.mock_lock_data(locker.written_data)

    package.add_dependency(Factory.create_dependency("b", "^2.0.0"))

    installer.whitelist(["b"])
    installer.update(True)
    result = installer.run()
    assert result == 0

    assert installer.executor.installations_count == 2


def test_installer_does_not_write_lock_file_when_installation_fails(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    mocker: MockerFixture,
) -> None:
    repo.add_package(get_package("A", "1.0"))
    package.add_dependency(Factory.create_dependency("A", "~1.0"))

    locker.locked(False)

    mocker.patch("poetry.installation.installer.Installer._execute", return_value=1)
    result = installer.run()
    assert result == 1  # error

    assert locker._lock_data is None

    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


@pytest.mark.parametrize("quiet", [True, False])
def test_run_with_dependencies_quiet(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    quiet: bool,
) -> None:
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    repo.add_package(package_a)
    repo.add_package(package_b)

    installer._io = BufferedIO(Input())
    installer._io.set_verbosity(Verbosity.QUIET if quiet else Verbosity.NORMAL)

    package.add_dependency(Factory.create_dependency("A", "~1.0"))
    package.add_dependency(Factory.create_dependency("B", "^1.0"))

    result = installer.run()
    assert result == 0

    expected = fixture("with-dependencies")
    assert locker.written_data == expected

    output = installer._io.fetch_output()
    if quiet:
        assert output == ""
    else:
        assert output != ""


@pytest.mark.parametrize("lock_version", ("1.1", "2.1"))
def test_installer_should_use_the_locked_version_of_git_dependencies(
    installer: Installer,
    locker: Locker,
    package: ProjectPackage,
    repo: Repository,
    lock_version: str,
) -> None:
    lock_data = {
        "package": [
            {
                "name": "demo",
                "version": "0.1.1",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
                "dependencies": {"pendulum": ">=1.4.4"},
                "source": {
                    "type": "git",
                    "url": "https://github.com/demo/demo.git",
                    "reference": "master",
                    "resolved_reference": "123456",
                },
            },
            {
                "name": "pendulum",
                "version": "1.4.4",
                "optional": False,
                "platform": "*",
                "python-versions": "*",
                "checksum": [],
                "dependencies": {},
            },
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "platform": "*",
            "content-hash": "123456789",
            "files": {"demo": [], "pendulum": []},
        },
    }
    fix_lock_data(lock_data)
    locker.locked(True)
    locker.mock_lock_data(lock_data)

    package.add_dependency(
        Factory.create_dependency(
            "demo", {"git": "https://github.com/demo/demo.git", "branch": "master"}
        )
    )

    repo.add_package(get_package("pendulum", "1.4.4"))

    result = installer.run()
    assert result == 0

    assert isinstance(installer.executor, TestExecutor)
    demo_installation = next(
        package
        for package in installer.executor.installations
        if package.name == "demo"
    )
    assert demo_installation == Package(
        "demo",
        "0.1.1",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference="master",
        source_resolved_reference="123456",
    )


@pytest.mark.parametrize("is_locked", [False, True])
def test_installer_should_use_the_locked_version_of_git_dependencies_with_extras(
    installer: Installer,
    locker: Locker,
    package: ProjectPackage,
    repo: Repository,
    is_locked: bool,
) -> None:
    if is_locked:
        locker.locked(True)
        locker.mock_lock_data(fixture("with-vcs-dependency-with-extras"))
        expected_reference = "123456"
    else:
        expected_reference = MOCK_DEFAULT_GIT_REVISION

    package.add_dependency(
        Factory.create_dependency(
            "demo",
            {
                "git": "https://github.com/demo/demo.git",
                "branch": "master",
                "extras": ["foo"],
            },
        )
    )

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cleo", "1.0.0"))

    result = installer.run()
    assert result == 0

    assert isinstance(installer.executor, TestExecutor)
    assert len(installer.executor.installations) == 3
    demo_installation = next(
        package
        for package in installer.executor.installations
        if package.name == "demo"
    )
    assert demo_installation == Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference="master",
        source_resolved_reference=expected_reference,
    )


@pytest.mark.parametrize("is_locked", [False, True])
def test_installer_should_use_the_locked_version_of_git_dependencies_without_reference(
    installer: Installer,
    locker: Locker,
    package: ProjectPackage,
    repo: Repository,
    is_locked: bool,
) -> None:
    """
    If there is no explicit reference (branch or tag or rev) in pyproject.toml,
    HEAD is used.
    """
    if is_locked:
        locker.locked(True)
        locker.mock_lock_data(fixture("with-vcs-dependency-without-ref"))
        expected_reference = "123456"
    else:
        expected_reference = MOCK_DEFAULT_GIT_REVISION

    package.add_dependency(
        Factory.create_dependency("demo", {"git": "https://github.com/demo/demo.git"})
    )

    repo.add_package(get_package("pendulum", "1.4.4"))

    result = installer.run()
    assert result == 0

    assert isinstance(installer.executor, TestExecutor)
    assert len(installer.executor.installations) == 2
    demo_installation = next(
        package
        for package in installer.executor.installations
        if package.name == "demo"
    )
    assert demo_installation == Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference="HEAD",
        source_resolved_reference=expected_reference,
    )


@pytest.mark.parametrize("lock_version", ("2.0", "2.1"))
@pytest.mark.parametrize("env_platform", ["darwin", "linux"])
def test_installer_distinguishes_locked_packages_with_local_version_by_source(
    pool: RepositoryPool,
    locker: Locker,
    installed: CustomInstalledRepository,
    config: Config,
    repo: Repository,
    package: ProjectPackage,
    env_platform: str,
    lock_version: str,
) -> None:
    """https://github.com/python-poetry/poetry/issues/6710"""
    # Require 1.11.0+cpu from pytorch for most platforms, but specify 1.11.0 and pypi on
    # darwin.
    package.add_dependency(
        Factory.create_dependency(
            "torch",
            {
                "version": "1.11.0+cpu",
                "markers": "sys_platform != 'darwin'",
                "source": "pytorch",
            },
        )
    )
    package.add_dependency(
        Factory.create_dependency(
            "torch",
            {
                "version": "1.11.0",
                "markers": "sys_platform == 'darwin'",
                "source": "pypi",
            },
        )
    )

    # Locking finds both the pypi and the pytorch packages.
    lock_data: dict[str, Any] = {
        "package": [
            {
                "name": "torch",
                "version": "1.11.0",
                "optional": False,
                "files": [],
                "python-versions": "*",
            },
            {
                "name": "torch",
                "version": "1.11.0+cpu",
                "optional": False,
                "files": [],
                "python-versions": "*",
                "source": {
                    "type": "legacy",
                    "url": "https://download.pytorch.org/whl",
                    "reference": "pytorch",
                },
            },
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
        },
    }
    if lock_version == "2.1":
        lock_data["package"][0]["groups"] = ["main"]
        lock_data["package"][0]["markers"] = "sys_platform == 'darwin'"
        lock_data["package"][1]["groups"] = ["main"]
        lock_data["package"][1]["markers"] = "sys_platform != 'darwin'"
    locker.locked(True)
    locker.mock_lock_data(lock_data)
    installer = Installer(
        NullIO(),
        MockEnv(platform=env_platform),
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=TestExecutor(
            MockEnv(platform=env_platform),
            pool,
            config,
            NullIO(),
        ),
    )
    result = installer.run()
    assert result == 0

    # Results of installation are consistent with the platform requirements.
    version = "1.11.0" if env_platform == "darwin" else "1.11.0+cpu"
    source_type = None if env_platform == "darwin" else "legacy"
    source_url = (
        None if env_platform == "darwin" else "https://download.pytorch.org/whl"
    )
    source_reference = None if env_platform == "darwin" else "pytorch"

    assert isinstance(installer.executor, TestExecutor)
    assert len(installer.executor.installations) == 1
    assert installer.executor.installations[0] == Package(
        "torch",
        version,
        source_type=source_type,
        source_url=source_url,
        source_reference=source_reference,
    )


@pytest.mark.parametrize("lock_version", ("2.0", "2.1"))
@pytest.mark.parametrize("env_platform_machine", ["aarch64", "amd64"])
def test_installer_distinguishes_locked_packages_with_same_version_by_source(
    pool: RepositoryPool,
    locker: Locker,
    installed: CustomInstalledRepository,
    config: Config,
    repo: Repository,
    package: ProjectPackage,
    env_platform_machine: str,
    lock_version: str,
) -> None:
    """https://github.com/python-poetry/poetry/issues/8303"""
    package.add_dependency(
        Factory.create_dependency(
            "kivy",
            {
                "version": "2.2.1",
                "markers": "platform_machine == 'aarch64'",
                "source": "pywheels",
            },
        )
    )
    package.add_dependency(
        Factory.create_dependency(
            "kivy",
            {
                "version": "2.2.1",
                "markers": "platform_machine != 'aarch64'",
                "source": "PyPI",
            },
        )
    )

    # Locking finds both the pypi and the pyhweels packages.
    lock_data: dict[str, Any] = {
        "package": [
            {
                "name": "kivy",
                "version": "2.2.1",
                "optional": False,
                "files": [],
                "python-versions": "*",
            },
            {
                "name": "kivy",
                "version": "2.2.1",
                "optional": False,
                "files": [],
                "python-versions": "*",
                "source": {
                    "type": "legacy",
                    "url": "https://www.piwheels.org/simple",
                    "reference": "pywheels",
                },
            },
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
        },
    }
    if lock_version == "2.1":
        lock_data["package"][0]["groups"] = ["main"]
        lock_data["package"][0]["markers"] = "platform_machine != 'aarch64'"
        lock_data["package"][1]["groups"] = ["main"]
        lock_data["package"][1]["markers"] = "platform_machine == 'aarch64'"
    locker.locked(True)
    locker.mock_lock_data(lock_data)
    installer = Installer(
        NullIO(),
        MockEnv(platform_machine=env_platform_machine),
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=TestExecutor(
            MockEnv(platform_machine=env_platform_machine),
            pool,
            config,
            NullIO(),
        ),
    )
    result = installer.run()
    assert result == 0

    # Results of installation are consistent with the platform requirements.
    version = "2.2.1"
    if env_platform_machine == "aarch64":
        source_type = "legacy"
        source_url = "https://www.piwheels.org/simple"
        source_reference = "pywheels"
    else:
        source_type = None
        source_url = None
        source_reference = None

    assert isinstance(installer.executor, TestExecutor)
    assert len(installer.executor.installations) == 1
    assert installer.executor.installations[0] == Package(
        "kivy",
        version,
        source_type=source_type,
        source_url=source_url,
        source_reference=source_reference,
    )


@pytest.mark.parametrize("lock_version", ("2.0", "2.1"))
@pytest.mark.parametrize("env_platform", ["darwin", "linux"])
def test_explicit_source_dependency_with_direct_origin_dependency(
    pool: RepositoryPool,
    locker: Locker,
    installed: CustomInstalledRepository,
    config: Config,
    repo: Repository,
    package: ProjectPackage,
    env_platform: str,
    lock_version: str,
) -> None:
    """
    A dependency with explicit source should not be satisfied by
    a direct origin dependency even if there is a version match.
    """
    demo_url = (
        "https://files.pythonhosted.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
    )
    package.add_dependency(
        Factory.create_dependency(
            "demo",
            {
                "markers": "sys_platform != 'darwin'",
                "url": demo_url,
            },
        )
    )
    package.add_dependency(
        Factory.create_dependency(
            "demo",
            {
                "version": "0.1.0",
                "markers": "sys_platform == 'darwin'",
                "source": "repo",
            },
        )
    )
    # The url demo dependency depends on pendulum.
    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("demo", "0.1.0"))

    # Locking finds both the direct origin and the explicit source packages.
    lock_data: dict[str, Any] = {
        "package": [
            {
                "name": "demo",
                "version": "0.1.0",
                "optional": False,
                "files": [],
                "python-versions": "*",
                "dependencies": {"pendulum": ">=1.4.4"},
                "source": {
                    "type": "url",
                    "url": demo_url,
                },
            },
            {
                "name": "demo",
                "version": "0.1.0",
                "optional": False,
                "files": [],
                "python-versions": "*",
                "source": {
                    "type": "legacy",
                    "url": "https://www.demo.org/simple",
                    "reference": "repo",
                },
            },
            {
                "name": "pendulum",
                "version": "1.4.4",
                "optional": False,
                "files": [],
                "python-versions": "*",
            },
        ],
        "metadata": {
            "lock-version": lock_version,
            "python-versions": "*",
            "content-hash": "123456789",
        },
    }
    if lock_version == "2.1":
        for locked_package in lock_data["package"]:
            locked_package["groups"] = ["main"]
        lock_data["package"][0]["markers"] = "sys_platform != 'darwin'"
        lock_data["package"][1]["markers"] = "sys_platform == 'darwin'"
        lock_data["package"][2]["markers"] = "sys_platform != 'darwin'"
    locker.locked(True)
    locker.mock_lock_data(lock_data)
    installer = Installer(
        NullIO(),
        MockEnv(platform=env_platform),
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=TestExecutor(
            MockEnv(platform=env_platform),
            pool,
            config,
            NullIO(),
        ),
    )

    result = installer.run()

    assert result == 0
    assert isinstance(installer.executor, TestExecutor)
    if env_platform == "linux":
        assert set(installer.executor.installations) == {
            Package("pendulum", "1.4.4"),
            Package(
                "demo",
                "0.1.0",
                source_type="url",
                source_url=demo_url,
            ),
        }
    else:
        assert installer.executor.installations == [
            Package(
                "demo",
                "0.1.0",
                source_type="legacy",
                source_url="https://www.demo.org/simple",
                source_reference="repo",
            )
        ]
