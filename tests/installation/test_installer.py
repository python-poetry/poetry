from __future__ import annotations

import itertools
import json

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

from cleo.io.inputs.input import Input
from cleo.io.io import IO
from cleo.io.null_io import NullIO
from cleo.io.outputs.buffered_output import BufferedOutput
from cleo.io.outputs.output import Verbosity
from poetry.core.packages.dependency_group import MAIN_GROUP
from poetry.core.packages.dependency_group import DependencyGroup
from poetry.core.packages.package import Package
from poetry.core.packages.project_package import ProjectPackage
from poetry.core.toml.file import TOMLFile

from poetry.factory import Factory
from poetry.installation import Installer as BaseInstaller
from poetry.installation.executor import Executor as BaseExecutor
from poetry.installation.noop_installer import NoopInstaller
from poetry.packages import Locker as BaseLocker
from poetry.repositories import Repository
from poetry.repositories import RepositoryPool
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils.env import MockEnv
from poetry.utils.env import NullEnv
from tests.helpers import MOCK_DEFAULT_GIT_REVISION
from tests.helpers import get_dependency
from tests.helpers import get_package
from tests.repositories.test_legacy_repository import (
    MockRepository as MockLegacyRepository,
)
from tests.repositories.test_pypi_repository import MockRepository


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from poetry.installation.operations.operation import Operation
    from poetry.packages import DependencyPackage
    from poetry.utils.env import Env
    from tests.conftest import Config
    from tests.types import FixtureDirGetter

RESERVED_PACKAGES = ("pip", "setuptools", "wheel")


class Installer(BaseInstaller):
    def _get_installer(self) -> NoopInstaller:
        return NoopInstaller()


class Executor(BaseExecutor):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self._installs: list[DependencyPackage] = []
        self._updates: list[DependencyPackage] = []
        self._uninstalls: list[DependencyPackage] = []

    @property
    def installations(self) -> list[DependencyPackage]:
        return self._installs

    @property
    def updates(self) -> list[DependencyPackage]:
        return self._updates

    @property
    def removals(self) -> list[DependencyPackage]:
        return self._uninstalls

    def _do_execute_operation(self, operation: Operation) -> None:
        super()._do_execute_operation(operation)

        if not operation.skipped:
            getattr(self, f"_{operation.job_type}s").append(operation.package)

    def _execute_install(self, operation: Operation) -> int:
        return 0

    def _execute_update(self, operation: Operation) -> int:
        return 0

    def _execute_uninstall(self, operation: Operation) -> int:
        return 0


class CustomInstalledRepository(InstalledRepository):
    @classmethod
    def load(
        cls, env: Env, with_dependencies: bool = False
    ) -> CustomInstalledRepository:
        return cls()


class Locker(BaseLocker):
    def __init__(self, lock_path: str | Path) -> None:
        self._lock = TOMLFile(Path(lock_path).joinpath("poetry.lock"))
        self._written_data = None
        self._locked = False
        self._content_hash = self._get_content_hash()

    @property
    def written_data(self) -> dict | None:
        return self._written_data

    def set_lock_path(self, lock: str | Path) -> Locker:
        self._lock = TOMLFile(Path(lock).joinpath("poetry.lock"))

        return self

    def locked(self, is_locked: bool = True) -> Locker:
        self._locked = is_locked

        return self

    def mock_lock_data(self, data: dict) -> None:
        self._lock_data = data

    def is_locked(self) -> bool:
        return self._locked

    def is_fresh(self) -> bool:
        return True

    def _get_content_hash(self) -> str:
        return "123456789"

    def _write_lock_data(self, data: dict) -> None:
        for package in data["package"]:
            python_versions = str(package["python-versions"])
            package["python-versions"] = python_versions

        self._written_data = json.loads(json.dumps(data))
        self._lock_data = data


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
    installer = Installer(
        NullIO(),
        env,
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=Executor(env, pool, config, NullIO()),
    )
    installer.use_executor(True)

    return installer


def fixture(name: str) -> dict:
    file = TOMLFile(Path(__file__).parent / "fixtures" / f"{name}.test")

    return json.loads(json.dumps(file.read()))


def test_run_no_dependencies(installer: Installer, locker: Locker):
    installer.run()
    expected = fixture("no-dependencies")

    assert locker.written_data == expected


def test_run_with_dependencies(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    repo.add_package(package_a)
    repo.add_package(package_b)

    package.add_dependency(Factory.create_dependency("A", "~1.0"))
    package.add_dependency(Factory.create_dependency("B", "^1.0"))

    installer.run()
    expected = fixture("with-dependencies")

    assert locker.written_data == expected


def test_run_update_after_removing_dependencies(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
):
    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "A",
                    "version": "1.0",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "B",
                    "version": "1.1",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "C",
                    "version": "1.2",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"A": [], "B": [], "C": []},
            },
        }
    )
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
    installer.run()
    expected = fixture("with-dependencies")

    assert locker.written_data == expected

    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 1


def _configure_run_install_dev(
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
    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "A",
                    "version": "1.0",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "B",
                    "version": "1.1",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "C",
                    "version": "1.2",
                    "category": "dev",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"A": [], "B": [], "C": []},
            },
        }
    )
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
):
    _configure_run_install_dev(
        locker,
        repo,
        package,
        installed,
        with_optional_group=True,
        with_packages_installed=with_packages_installed,
    )

    if groups is not None:
        installer.only_groups(groups)

    installer.requires_synchronization(True)
    installer.run()

    assert installer.executor.installations_count == installs
    assert installer.executor.updates_count == updates
    assert installer.executor.removals_count == removals


def test_run_install_does_not_remove_locked_packages_if_installed_but_not_required(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
):
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

    package.add_dependency(Factory.create_dependency(package_a.name, package_a.version))

    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": package_a.name,
                    "version": package_a.version.text,
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": package_b.name,
                    "version": package_b.version.text,
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": package_c.name,
                    "version": package_c.version.text,
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {package_a.name: [], package_b.name: [], package_c.name: []},
            },
        }
    )

    installer.run()

    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_run_install_removes_locked_packages_if_installed_and_synchronization_is_required(  # noqa: E501
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
):
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

    package.add_dependency(Factory.create_dependency(package_a.name, package_a.version))

    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": package_a.name,
                    "version": package_a.version.text,
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": package_b.name,
                    "version": package_b.version.text,
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": package_c.name,
                    "version": package_c.version.text,
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {package_a.name: [], package_b.name: [], package_c.name: []},
            },
        }
    )

    installer.requires_synchronization(True)
    installer.run()

    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 2


def test_run_install_removes_no_longer_locked_packages_if_installed(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
):
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

    package.add_dependency(Factory.create_dependency(package_a.name, package_a.version))

    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": package_a.name,
                    "version": package_a.version.text,
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": package_b.name,
                    "version": package_b.version.text,
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": package_c.name,
                    "version": package_c.version.text,
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {package_a.name: [], package_b.name: [], package_c.name: []},
            },
        }
    )

    installer.update(True)
    installer.run()

    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 2


@pytest.mark.parametrize(
    "managed_reserved_package_names",
    itertools.chain(
        [()],
        itertools.permutations(RESERVED_PACKAGES, 1),
        itertools.permutations(RESERVED_PACKAGES, 2),
        [RESERVED_PACKAGES],
    ),
)
def test_run_install_with_synchronization(
    managed_reserved_package_names: tuple[str, ...],
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
):
    package_a = get_package("a", "1.0")
    package_b = get_package("b", "1.1")
    package_c = get_package("c", "1.2")
    package_pip = get_package("pip", "20.0.0")
    package_setuptools = get_package("setuptools", "20.0.0")
    package_wheel = get_package("wheel", "20.0.0")

    all_packages = [
        package_a,
        package_b,
        package_c,
        package_pip,
        package_setuptools,
        package_wheel,
    ]

    managed_reserved_packages = [
        pkg for pkg in all_packages if pkg.name in managed_reserved_package_names
    ]
    locked_packages = [package_a, *managed_reserved_packages]

    for pkg in all_packages:
        repo.add_package(pkg)
        installed.add_package(pkg)

    installed.add_package(package)  # Root package never removed.

    package.add_dependency(Factory.create_dependency(package_a.name, package_a.version))

    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": pkg.name,
                    "version": pkg.version,
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                }
                for pkg in locked_packages
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {pkg.name: [] for pkg in locked_packages},
            },
        }
    )

    installer.requires_synchronization(True)
    installer.run()

    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert 2 + len(managed_reserved_packages) == installer.executor.removals_count

    expected_removals = {
        package_b.name,
        package_c.name,
        *managed_reserved_package_names,
    }

    assert {r.name for r in installer.executor.removals} == expected_removals


def test_run_whitelist_add(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "A",
                    "version": "1.0",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                }
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"A": []},
            },
        }
    )
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

    installer.run()
    expected = fixture("with-dependencies")

    assert locker.written_data == expected


def test_run_whitelist_remove(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
):
    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "A",
                    "version": "1.0",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "B",
                    "version": "1.1",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"A": [], "B": []},
            },
        }
    )
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    repo.add_package(package_a)
    repo.add_package(package_b)
    installed.add_package(package_b)

    package.add_dependency(Factory.create_dependency("A", "~1.0"))

    installer.update(True)
    installer.whitelist(["B"])

    installer.run()
    expected = fixture("remove")

    assert locker.written_data == expected
    assert installer.executor.installations_count == 1
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 1


def test_add_with_sub_dependencies(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
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

    installer.run()
    expected = fixture("with-sub-dependencies")

    assert locker.written_data == expected


def test_run_with_python_versions(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
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

    installer.run()
    expected = fixture("with-python-versions")

    assert locker.written_data == expected


def test_run_with_optional_and_python_restricted_dependencies(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
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

    package.extras = {"foo": [get_dependency("A", "~1.0")]}
    package.add_dependency(
        Factory.create_dependency("A", {"version": "~1.0", "optional": True})
    )
    package.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "python": "~2.4"})
    )
    package.add_dependency(
        Factory.create_dependency("C", {"version": "^1.0", "python": "~2.7 || ^3.4"})
    )

    installer.run()
    expected = fixture("with-optional-dependencies")

    assert locker.written_data == expected

    # We should only have 2 installs:
    # C,D since python version is not compatible
    # with B's python constraint and A is optional
    assert installer.executor.installations_count == 2
    assert installer.executor.installations[0].name == "d"
    assert installer.executor.installations[1].name == "c"


def test_run_with_optional_and_platform_restricted_dependencies(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    mocker: MockerFixture,
):
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

    package.extras = {"foo": [get_dependency("A", "~1.0")]}
    package.add_dependency(
        Factory.create_dependency("A", {"version": "~1.0", "optional": True})
    )
    package.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "platform": "custom"})
    )
    package.add_dependency(
        Factory.create_dependency("C", {"version": "^1.0", "platform": "darwin"})
    )

    installer.run()
    expected = fixture("with-platform-dependencies")

    assert locker.written_data == expected

    # We should only have 2 installs:
    # C,D since the mocked python version is not compatible
    # with B's python constraint and A is optional
    assert installer.executor.installations_count == 2
    assert installer.executor.installations[0].name == "d"
    assert installer.executor.installations[1].name == "c"


def test_run_with_dependencies_extras(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")

    package_b.extras = {"foo": [get_dependency("C", "^1.0")]}
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

    installer.run()
    expected = fixture("with-dependencies-extras")

    assert locker.written_data == expected


def test_run_with_dependencies_nested_extras(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")

    dependency_c = Factory.create_dependency("C", {"version": "^1.0", "optional": True})
    dependency_b = Factory.create_dependency(
        "B", {"version": "^1.0", "optional": True, "extras": ["C"]}
    )
    dependency_a = Factory.create_dependency("A", {"version": "^1.0", "extras": ["B"]})

    package_b.extras = {"c": [dependency_c]}
    package_b.add_dependency(dependency_c)

    package_a.add_dependency(dependency_b)
    package_a.extras = {"b": [dependency_b]}

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    package.add_dependency(dependency_a)

    installer.run()
    expected = fixture("with-dependencies-nested-extras")

    assert locker.written_data == expected


def test_run_does_not_install_extras_if_not_requested(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
    package.extras["foo"] = [get_dependency("D")]
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
    package.add_dependency(Factory.create_dependency("C", "^1.0"))
    package.add_dependency(
        Factory.create_dependency("D", {"version": "^1.0", "optional": True})
    )

    installer.run()
    expected = fixture("extras")

    # Extras are pinned in lock
    assert locker.written_data == expected

    # But should not be installed
    assert installer.executor.installations_count == 3  # A, B, C


def test_run_installs_extras_if_requested(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
    package.extras["foo"] = [get_dependency("D")]
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
    package.add_dependency(Factory.create_dependency("C", "^1.0"))
    package.add_dependency(
        Factory.create_dependency("D", {"version": "^1.0", "optional": True})
    )

    installer.extras(["foo"])
    installer.run()
    expected = fixture("extras")

    # Extras are pinned in lock
    assert locker.written_data == expected

    # But should not be installed
    assert installer.executor.installations_count == 4  # A, B, C, D


def test_run_installs_extras_with_deps_if_requested(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
    package.extras["foo"] = [get_dependency("C")]
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
    package.add_dependency(
        Factory.create_dependency("C", {"version": "^1.0", "optional": True})
    )

    package_c.add_dependency(Factory.create_dependency("D", "^1.0"))

    installer.extras(["foo"])
    installer.run()
    expected = fixture("extras-with-dependencies")

    # Extras are pinned in lock
    assert locker.written_data == expected

    # But should not be installed
    assert installer.executor.installations_count == 4  # A, B, C, D


def test_run_installs_extras_with_deps_if_requested_locked(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
    locker.locked(True)
    locker.mock_lock_data(fixture("extras-with-dependencies"))
    package.extras["foo"] = [get_dependency("C")]
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
    package.add_dependency(
        Factory.create_dependency("C", {"version": "^1.0", "optional": True})
    )

    package_c.add_dependency(Factory.create_dependency("D", "^1.0"))

    installer.extras(["foo"])
    installer.run()

    # But should not be installed
    assert installer.executor.installations_count == 4  # A, B, C, D


def test_installer_with_pypi_repository(
    package: ProjectPackage,
    locker: Locker,
    installed: CustomInstalledRepository,
    config: Config,
    env: NullEnv,
):
    pool = RepositoryPool()
    pool.add_repository(MockRepository())

    installer = Installer(
        NullIO(), env, package, locker, pool, config, installed=installed
    )

    package.add_dependency(Factory.create_dependency("pytest", "^3.5", groups=["dev"]))
    installer.run()

    expected = fixture("with-pypi-repository")

    assert expected == locker.written_data


def test_run_installs_with_local_file(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: FixtureDirGetter,
):
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

    installer.run()

    expected = fixture("with-file-dependency")

    assert locker.written_data == expected
    assert installer.executor.installations_count == 2


def test_run_installs_wheel_with_no_requires_dist(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: FixtureDirGetter,
):
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

    installer.run()

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
):
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

    installer.run()

    expected = fixture("with-directory-dependency-poetry")
    assert locker.written_data == expected

    assert installer.executor.installations_count == 2


def test_run_installs_with_local_poetry_directory_transitive(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    tmpdir: Path,
    fixture_dir: FixtureDirGetter,
):
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

    installer.run()

    expected = fixture("with-directory-dependency-poetry-transitive")

    assert locker.written_data == expected

    assert installer.executor.installations_count == 6


def test_run_installs_with_local_poetry_file_transitive(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    tmpdir: str,
    fixture_dir: FixtureDirGetter,
):
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

    installer.run()

    expected = fixture("with-file-dependency-transitive")

    assert locker.written_data == expected

    assert installer.executor.installations_count == 4


def test_run_installs_with_local_setuptools_directory(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    tmpdir: Path,
    fixture_dir: FixtureDirGetter,
):
    root_dir = Path(__file__).parent.parent.parent
    package.root_dir = root_dir
    locker.set_lock_path(root_dir)
    file_path = fixture_dir("project_with_setup/")
    package.add_dependency(
        Factory.create_dependency(
            "project-with-setup",
            {"path": str(file_path.relative_to(root_dir))},
            root_dir=root_dir,
        )
    )

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cachy", "0.2.0"))

    installer.run()

    expected = fixture("with-directory-dependency-setuptools")

    assert locker.written_data == expected
    assert installer.executor.installations_count == 3


def test_run_with_prereleases(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "A",
                    "version": "1.0a2",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                }
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"A": []},
            },
        }
    )
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

    installer.run()
    expected = fixture("with-prereleases")

    assert locker.written_data == expected


def test_run_changes_category_if_needed(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "A",
                    "version": "1.0",
                    "category": "dev",
                    "optional": True,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                }
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"A": []},
            },
        }
    )
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    package_b.add_dependency(Factory.create_dependency("A", "^1.0"))
    repo.add_package(package_a)
    repo.add_package(package_b)

    package.add_dependency(
        Factory.create_dependency(
            "A", {"version": "^1.0", "optional": True}, groups=["dev"]
        )
    )
    package.add_dependency(Factory.create_dependency("B", "^1.1"))

    installer.update(True)
    installer.whitelist(["B"])

    installer.run()
    expected = fixture("with-category-change")

    assert locker.written_data == expected


def test_run_update_all_with_lock(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "A",
                    "version": "1.0",
                    "category": "dev",
                    "optional": True,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                }
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"A": []},
            },
        }
    )
    package_a = get_package("A", "1.1")
    repo.add_package(get_package("A", "1.0"))
    repo.add_package(package_a)

    package.add_dependency(Factory.create_dependency("A", "*"))

    installer.update(True)

    installer.run()
    expected = fixture("update-with-lock")

    assert locker.written_data == expected


def test_run_update_with_locked_extras(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "A",
                    "version": "1.0",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "dependencies": {"B": "^1.0", "C": "^1.0"},
                },
                {
                    "name": "B",
                    "version": "1.0",
                    "category": "dev",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "C",
                    "version": "1.1",
                    "category": "dev",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "requirements": {"python": "~2.7"},
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"A": [], "B": [], "C": []},
            },
        }
    )
    package_a = get_package("A", "1.0")
    package_a.extras["foo"] = [get_dependency("B")]
    b_dependency = get_dependency("B", "^1.0", optional=True)
    b_dependency.in_extras.append("foo")
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

    installer.run()
    expected = fixture("update-with-locked-extras")

    assert locker.written_data == expected


def test_run_install_duplicate_dependencies_different_constraints(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
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

    installer.run()

    expected = fixture("with-duplicate-dependencies")

    assert locker.written_data == expected

    installs = installer.executor.installations
    assert installer.executor.installations_count == 3
    assert installs[0] == package_c12
    assert installs[1] == package_b10
    assert installs[2] == package_a

    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_run_install_duplicate_dependencies_different_constraints_with_lock(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "A",
                    "version": "1.0",
                    "category": "main",
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
                    "category": "dev",
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
                    "category": "dev",
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
                    "category": "dev",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "C",
                    "version": "1.5",
                    "category": "dev",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"A": [], "B": [], "C": []},
            },
        }
    )
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
    installer.run()

    expected = fixture("with-duplicate-dependencies")

    assert locker.written_data == expected

    assert installer.executor.installations_count == 3
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_run_update_uninstalls_after_removal_transient_dependency(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
):
    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "A",
                    "version": "1.0",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "dependencies": {"B": {"version": "^1.0", "python": "<2.0"}},
                },
                {
                    "name": "B",
                    "version": "1.0",
                    "category": "dev",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"A": [], "B": []},
            },
        }
    )
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
    installer.run()

    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 1


def test_run_install_duplicate_dependencies_different_constraints_with_lock_update(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
):
    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "A",
                    "version": "1.0",
                    "category": "main",
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
                    "category": "dev",
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
                    "category": "dev",
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
                    "category": "dev",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
                {
                    "name": "C",
                    "version": "1.5",
                    "category": "dev",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"A": [], "B": [], "C": []},
            },
        }
    )
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
    installer.run()

    expected = fixture("with-duplicate-dependencies-update")

    assert locker.written_data == expected

    assert installer.executor.installations_count == 2
    assert installer.executor.updates_count == 1
    assert installer.executor.removals_count == 0


@pytest.mark.skip(
    "This is not working at the moment due to limitations in the resolver"
)
def test_installer_test_solver_finds_compatible_package_for_dependency_python_not_fully_compatible_with_package_python(  # noqa: E501
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
):
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

    installer.run()

    expected = fixture("with-conditional-dependency")
    assert locker.written_data == expected
    assert installer.executor.installations_count == 1


def test_installer_required_extras_should_not_be_removed_when_updating_single_dependency(  # noqa: E501
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    env: NullEnv,
    pool: RepositoryPool,
    config: Config,
):
    package.add_dependency(Factory.create_dependency("A", {"version": "^1.0"}))

    package_a = get_package("A", "1.0.0")
    package_a.add_dependency(
        Factory.create_dependency("B", {"version": "^1.0", "extras": ["foo"]})
    )

    package_b = get_package("B", "1.0.0")
    package_b.add_dependency(
        Factory.create_dependency("C", {"version": "^1.0", "optional": True})
    )
    package_b.extras = {"foo": [get_dependency("C")]}

    package_c = get_package("C", "1.0.0")
    package_d = get_package("D", "1.0.0")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    installer.update(True)
    installer.run()

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
        executor=Executor(env, pool, config, NullIO()),
    )
    installer.use_executor()

    installer.update(True)
    installer.whitelist(["D"])
    installer.run()

    assert installer.executor.installations_count == 1
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_installer_required_extras_should_not_be_removed_when_updating_single_dependency_pypi_repository(  # noqa: E501
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    env: NullEnv,
    mocker: MockerFixture,
    config: Config,
):
    mocker.patch("sys.platform", "darwin")

    pool = RepositoryPool()
    pool.add_repository(MockRepository())

    installer = Installer(
        NullIO(),
        env,
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=Executor(env, pool, config, NullIO()),
    )
    installer.use_executor()

    package.add_dependency(Factory.create_dependency("poetry", {"version": "^0.12.0"}))

    installer.update(True)
    installer.run()

    assert installer.executor.installations_count == 3
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0

    package.add_dependency(Factory.create_dependency("pytest", "^3.5"))

    locker.locked(True)
    locker.mock_lock_data(locker.written_data)

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
        executor=Executor(env, pool, config, NullIO()),
    )
    installer.use_executor()

    installer.update(True)
    installer.whitelist(["pytest"])
    installer.run()

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
):
    pool = RepositoryPool()
    pool.add_repository(MockRepository())

    installer = Installer(
        NullIO(),
        env,
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=Executor(env, pool, config, NullIO()),
    )
    installer.use_executor()

    package.add_dependency(
        Factory.create_dependency(
            "cachecontrol", {"version": "^0.12.5", "extras": ["filecache"]}
        )
    )

    installer.update(True)
    installer.run()

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
        executor=Executor(env, pool, config, NullIO()),
    )
    installer.use_executor()

    installer.update(True)
    installer.run()

    assert installer.executor.installations_count == 2
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_update_multiple_times_with_split_dependencies_is_idempotent(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "A",
                    "version": "1.0",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "dependencies": {"B": ">=1.0"},
                },
                {
                    "name": "B",
                    "version": "1.0.1",
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": ">=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*",
                    "checksum": [],
                    "dependencies": {},
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"A": [], "B": []},
            },
        }
    )

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
    installer.run()

    assert locker.written_data == expected

    locker.mock_lock_data(locker.written_data)

    installer.update(True)
    installer.run()

    assert locker.written_data == expected

    locker.mock_lock_data(locker.written_data)

    installer.update(True)
    installer.run()

    assert locker.written_data == expected


def test_installer_can_install_dependencies_from_forced_source(
    locker: Locker,
    package: Package,
    installed: CustomInstalledRepository,
    env: NullEnv,
    config: Config,
):
    package.python_versions = "^3.7"
    package.add_dependency(
        Factory.create_dependency("tomlkit", {"version": "^0.5", "source": "legacy"})
    )

    pool = RepositoryPool()
    pool.add_repository(MockLegacyRepository())
    pool.add_repository(MockRepository())

    installer = Installer(
        NullIO(),
        env,
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=Executor(env, pool, config, NullIO()),
    )
    installer.use_executor()

    installer.update(True)
    installer.run()

    assert installer.executor.installations_count == 1
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_run_installs_with_url_file(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
    url = "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
    package.add_dependency(Factory.create_dependency("demo", {"url": url}))

    repo.add_package(get_package("pendulum", "1.4.4"))

    installer.run()

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
        "linux": "https://python-poetry.org/distributions/demo-0.1.0.tar.gz",
        "win32": (
            "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
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
        executor=Executor(
            MockEnv(platform=env_platform),
            pool,
            config,
            NullIO(),
        ),
    )
    installer.use_executor(True)
    installer.run()

    expected = fixture("with-same-version-url-dependencies")
    assert locker.written_data == expected
    assert installer.executor.installations_count == 2
    demo_package = next(p for p in installer.executor.installations if p.name == "demo")
    assert demo_package.source_url == urls[env_platform]


def test_installer_uses_prereleases_if_they_are_compatible(
    installer: Installer, locker: Locker, package: ProjectPackage, repo: Repository
):
    package.python_versions = "~2.7 || ^3.4"
    package.add_dependency(
        Factory.create_dependency(
            "prerelease", {"git": "https://github.com/demo/prerelease.git"}
        )
    )

    package_b = get_package("b", "2.0.0")
    package_b.add_dependency(Factory.create_dependency("prerelease", ">=0.19"))

    repo.add_package(package_b)

    installer.run()

    del installer.installer.installs[:]
    locker.locked(True)
    locker.mock_lock_data(locker.written_data)

    package.add_dependency(Factory.create_dependency("b", "^2.0.0"))

    installer.whitelist(["b"])
    installer.update(True)
    installer.run()

    assert installer.executor.installations_count == 2


def test_installer_can_handle_old_lock_files(
    locker: Locker,
    package: ProjectPackage,
    repo: Repository,
    installed: CustomInstalledRepository,
    config: Config,
):
    pool = RepositoryPool()
    pool.add_repository(MockRepository())

    package.add_dependency(Factory.create_dependency("pytest", "^3.5", groups=["dev"]))

    locker.locked()
    locker.mock_lock_data(fixture("old-lock"))

    installer = Installer(
        NullIO(),
        MockEnv(),
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=Executor(MockEnv(), pool, config, NullIO()),
    )
    installer.use_executor()

    installer.run()

    assert installer.executor.installations_count == 6

    installer = Installer(
        NullIO(),
        MockEnv(version_info=(2, 7, 18)),
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=Executor(
            MockEnv(version_info=(2, 7, 18)),
            pool,
            config,
            NullIO(),
        ),
    )
    installer.use_executor()

    installer.run()

    # funcsigs will be added
    assert installer.executor.installations_count == 7

    installer = Installer(
        NullIO(),
        MockEnv(version_info=(2, 7, 18), platform="win32"),
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=Executor(
            MockEnv(version_info=(2, 7, 18), platform="win32"),
            pool,
            config,
            NullIO(),
        ),
    )
    installer.use_executor()

    installer.run()

    # colorama will be added
    assert installer.executor.installations_count == 8


@pytest.mark.parametrize("quiet", [True, False])
def test_run_with_dependencies_quiet(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    quiet: bool,
):
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    repo.add_package(package_a)
    repo.add_package(package_b)

    installer._io = IO(Input(), BufferedOutput(), BufferedOutput())
    installer._io.set_verbosity(Verbosity.QUIET if quiet else Verbosity.NORMAL)

    package.add_dependency(Factory.create_dependency("A", "~1.0"))
    package.add_dependency(Factory.create_dependency("B", "^1.0"))

    installer.run()
    expected = fixture("with-dependencies")

    assert locker.written_data == expected

    installer._io.output._buffer.seek(0)
    if quiet:
        assert installer._io.output._buffer.read() == ""
    else:
        assert installer._io.output._buffer.read() != ""


def test_installer_should_use_the_locked_version_of_git_dependencies(
    installer: Installer, locker: Locker, package: ProjectPackage, repo: Repository
):
    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "demo",
                    "version": "0.1.1",
                    "category": "main",
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
                    "category": "main",
                    "optional": False,
                    "platform": "*",
                    "python-versions": "*",
                    "checksum": [],
                    "dependencies": {},
                },
            ],
            "metadata": {
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
                "files": {"demo": [], "pendulum": []},
            },
        }
    )

    package.add_dependency(
        Factory.create_dependency(
            "demo", {"git": "https://github.com/demo/demo.git", "branch": "master"}
        )
    )

    repo.add_package(get_package("pendulum", "1.4.4"))

    installer.run()

    assert installer.executor.installations[-1] == Package(
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
):
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

    installer.run()

    assert len(installer.executor.installations) == 3
    assert installer.executor.installations[-1] == Package(
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
):
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

    installer.run()

    assert len(installer.executor.installations) == 2
    assert installer.executor.installations[-1] == Package(
        "demo",
        "0.1.2",
        source_type="git",
        source_url="https://github.com/demo/demo.git",
        source_reference="HEAD",
        source_resolved_reference=expected_reference,
    )


# https://github.com/python-poetry/poetry/issues/6710
@pytest.mark.parametrize("env_platform", ["darwin", "linux"])
def test_installer_distinguishes_locked_packages_by_source(
    pool: RepositoryPool,
    locker: Locker,
    installed: CustomInstalledRepository,
    config: Config,
    repo: Repository,
    package: ProjectPackage,
    env_platform: str,
):
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
    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "torch",
                    "version": "1.11.0",
                    "category": "main",
                    "optional": False,
                    "files": [],
                    "python-versions": "*",
                },
                {
                    "name": "torch",
                    "version": "1.11.0+cpu",
                    "category": "main",
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
                "python-versions": "*",
                "platform": "*",
                "content-hash": "123456789",
            },
        }
    )
    installer = Installer(
        NullIO(),
        MockEnv(platform=env_platform),
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=Executor(
            MockEnv(platform=env_platform),
            pool,
            config,
            NullIO(),
        ),
    )
    installer.use_executor(True)
    installer.run()

    # Results of installation are consistent with the platform requirements.
    version = "1.11.0" if env_platform == "darwin" else "1.11.0+cpu"
    source_type = None if env_platform == "darwin" else "legacy"
    source_url = (
        None if env_platform == "darwin" else "https://download.pytorch.org/whl"
    )
    source_reference = None if env_platform == "darwin" else "pytorch"

    assert len(installer.executor.installations) == 1
    assert installer.executor.installations[0] == Package(
        "torch",
        version,
        source_type=source_type,
        source_url=source_url,
        source_reference=source_reference,
    )
