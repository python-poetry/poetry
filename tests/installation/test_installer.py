<<<<<<< HEAD
import itertools
import json

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
=======
from __future__ import unicode_literals

import itertools
import json
import sys

from pathlib import Path
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

import pytest

from cleo.io.inputs.input import Input
from cleo.io.io import IO
from cleo.io.null_io import NullIO
from cleo.io.outputs.buffered_output import BufferedOutput
from cleo.io.outputs.output import Verbosity
from deepdiff import DeepDiff
<<<<<<< HEAD
=======

>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
from poetry.core.packages.dependency_group import DependencyGroup
from poetry.core.packages.package import Package
from poetry.core.packages.project_package import ProjectPackage
from poetry.core.toml.file import TOMLFile
<<<<<<< HEAD

=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
from poetry.factory import Factory
from poetry.installation import Installer as BaseInstaller
from poetry.installation.executor import Executor as BaseExecutor
from poetry.installation.noop_installer import NoopInstaller
from poetry.packages import Locker as BaseLocker
from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils.env import MockEnv
from poetry.utils.env import NullEnv
from tests.helpers import get_dependency
from tests.helpers import get_package
from tests.repositories.test_legacy_repository import (
    MockRepository as MockLegacyRepository,
)
from tests.repositories.test_pypi_repository import MockRepository


<<<<<<< HEAD
if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from poetry.installation.operations import OperationTypes
    from poetry.packages import DependencyPackage
    from poetry.utils.env import Env
    from tests.conftest import Config
    from tests.types import FixtureDirGetter

=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
RESERVED_PACKAGES = ("pip", "setuptools", "wheel")


class Installer(BaseInstaller):
<<<<<<< HEAD
    def _get_installer(self) -> NoopInstaller:
=======
    def _get_installer(self):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        return NoopInstaller()


class Executor(BaseExecutor):
<<<<<<< HEAD
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self._installs: List["DependencyPackage"] = []
        self._updates: List["DependencyPackage"] = []
        self._uninstalls: List["DependencyPackage"] = []

    @property
    def installations(self) -> List["DependencyPackage"]:
        return self._installs

    @property
    def updates(self) -> List["DependencyPackage"]:
        return self._updates

    @property
    def removals(self) -> List["DependencyPackage"]:
        return self._uninstalls

    def _do_execute_operation(self, operation: "OperationTypes") -> None:
        super()._do_execute_operation(operation)

        if not operation.skipped:
            getattr(self, f"_{operation.job_type}s").append(operation.package)

    def _execute_install(self, operation: "OperationTypes") -> int:
        return 0

    def _execute_update(self, operation: "OperationTypes") -> int:
        return 0

    def _execute_uninstall(self, operation: "OperationTypes") -> int:
=======
    def __init__(self, *args, **kwargs):
        super(Executor, self).__init__(*args, **kwargs)

        self._installs = []
        self._updates = []
        self._uninstalls = []

    @property
    def installations(self):
        return self._installs

    @property
    def updates(self):
        return self._updates

    @property
    def removals(self):
        return self._uninstalls

    def _do_execute_operation(self, operation):
        super(Executor, self)._do_execute_operation(operation)

        if not operation.skipped:
            getattr(self, "_{}s".format(operation.job_type)).append(operation.package)

    def _execute_install(self, operation):
        return 0

    def _execute_update(self, operation):
        return 0

    def _execute_uninstall(self, operation):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        return 0


class CustomInstalledRepository(InstalledRepository):
    @classmethod
<<<<<<< HEAD
    def load(
        cls, env: "Env", with_dependencies: bool = False
    ) -> "CustomInstalledRepository":
=======
    def load(cls, env):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        return cls()


class Locker(BaseLocker):
<<<<<<< HEAD
    def __init__(self, lock_path: Union[str, Path]):
        self._lock = TOMLFile(Path(lock_path).joinpath("poetry.lock"))
=======
    def __init__(self):
        self._lock = TOMLFile(Path.cwd().joinpath("poetry.lock"))
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        self._written_data = None
        self._locked = False
        self._content_hash = self._get_content_hash()

    @property
<<<<<<< HEAD
    def written_data(self) -> Optional[Dict]:
        return self._written_data

    def set_lock_path(self, lock: Union[str, Path]) -> "Locker":
=======
    def written_data(self):
        return self._written_data

    def set_lock_path(self, lock):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        self._lock = TOMLFile(Path(lock).joinpath("poetry.lock"))

        return self

<<<<<<< HEAD
    def locked(self, is_locked: bool = True) -> "Locker":
=======
    def locked(self, is_locked=True):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        self._locked = is_locked

        return self

<<<<<<< HEAD
    def mock_lock_data(self, data: Dict) -> None:
        self._lock_data = data

    def is_locked(self) -> bool:
        return self._locked

    def is_fresh(self) -> bool:
        return True

    def _get_content_hash(self) -> str:
        return "123456789"

    def _write_lock_data(self, data: Dict) -> None:
=======
    def mock_lock_data(self, data):
        self._lock_data = data

    def is_locked(self):
        return self._locked

    def is_fresh(self):
        return True

    def _get_content_hash(self):
        return "123456789"

    def _write_lock_data(self, data):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        for package in data["package"]:
            python_versions = str(package["python-versions"])
            package["python-versions"] = python_versions

        self._written_data = json.loads(json.dumps(data))
        self._lock_data = data


@pytest.fixture()
<<<<<<< HEAD
def package() -> ProjectPackage:
=======
def package():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    p = ProjectPackage("root", "1.0")
    p.root_dir = Path.cwd()

    return p


@pytest.fixture()
<<<<<<< HEAD
def repo() -> Repository:
=======
def repo():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return Repository()


@pytest.fixture()
<<<<<<< HEAD
def pool(repo: Repository) -> Pool:
=======
def pool(repo):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    pool = Pool()
    pool.add_repository(repo)

    return pool


@pytest.fixture()
<<<<<<< HEAD
def installed() -> CustomInstalledRepository:
=======
def installed():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return CustomInstalledRepository()


@pytest.fixture()
<<<<<<< HEAD
def locker(project_root: Path) -> Locker:
    return Locker(lock_path=project_root)


@pytest.fixture()
def env() -> NullEnv:
=======
def locker():
    return Locker()


@pytest.fixture()
def env():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return NullEnv()


@pytest.fixture()
<<<<<<< HEAD
def installer(
    package: ProjectPackage,
    pool: Pool,
    locker: Locker,
    env: NullEnv,
    installed: CustomInstalledRepository,
    config: "Config",
) -> Installer:
=======
def installer(package, pool, locker, env, installed, config):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def fixture(name: str) -> Dict:
    file = TOMLFile(Path(__file__).parent / "fixtures" / f"{name}.test")
=======
def fixture(name):
    file = TOMLFile(Path(__file__).parent / "fixtures" / "{}.test".format(name))
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

    return json.loads(json.dumps(file.read()))


<<<<<<< HEAD
def test_run_no_dependencies(installer: Installer, locker: Locker):
=======
def test_run_no_dependencies(installer, locker):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    installer.run()
    expected = fixture("no-dependencies")

    assert locker.written_data == expected


<<<<<<< HEAD
def test_run_with_dependencies(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
=======
def test_run_with_dependencies(installer, locker, repo, package):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
<<<<<<< HEAD
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
=======
    installer, locker, repo, package, installed
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {"A": [], "B": [], "C": []},
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

<<<<<<< HEAD
    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 1


def _configure_run_install_dev(
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    with_optional_group: bool = False,
) -> None:
=======
    assert 0 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 1 == installer.executor.removals_count


def _configure_run_install_dev(
    locker, repo, package, installed, with_optional_group=False
):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {"A": [], "B": [], "C": []},
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

    group = DependencyGroup("dev", optional=with_optional_group)
    group.add_dependency(Factory.create_dependency("C", "~1.2", groups=["dev"]))
    package.add_dependency_group(group)


<<<<<<< HEAD
def test_run_install_no_group(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
):
=======
def test_run_install_no_group(installer, locker, repo, package, installed):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    _configure_run_install_dev(locker, repo, package, installed)

    installer.without_groups(["dev"])
    installer.run()

<<<<<<< HEAD
    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_run_install_group_only(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
):
=======
    assert 0 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_run_install_group_only(installer, locker, repo, package, installed):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    _configure_run_install_dev(locker, repo, package, installed)

    installer.only_groups(["dev"])
    installer.run()

<<<<<<< HEAD
    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_run_install_with_optional_group_not_selected(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
=======
    assert 0 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_run_install_with_optional_group_not_selected(
    installer, locker, repo, package, installed
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    _configure_run_install_dev(
        locker, repo, package, installed, with_optional_group=True
    )

    installer.run()

<<<<<<< HEAD
    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_run_install_does_not_remove_locked_packages_if_installed_but_not_required(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
=======
    assert 0 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_run_install_does_not_remove_locked_packages_if_installed_but_not_required(
    installer, locker, repo, package, installed
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {package_a.name: [], package_b.name: [], package_c.name: []},
            },
        }
    )

    installer.run()

<<<<<<< HEAD
    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_run_install_removes_locked_packages_if_installed_and_synchronization_is_required(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
=======
    assert 0 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_run_install_removes_locked_packages_if_installed_and_synchronization_is_required(
    installer, locker, repo, package, installed
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {package_a.name: [], package_b.name: [], package_c.name: []},
            },
        }
    )

    installer.requires_synchronization(True)
    installer.run()

<<<<<<< HEAD
    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 2


def test_run_install_removes_no_longer_locked_packages_if_installed(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
=======
    assert 0 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 2 == installer.executor.removals_count


def test_run_install_removes_no_longer_locked_packages_if_installed(
    installer, locker, repo, package, installed
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {package_a.name: [], package_b.name: [], package_c.name: []},
            },
        }
    )

    installer.update(True)
    installer.run()

<<<<<<< HEAD
    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 2


def test_run_install_with_optional_group_selected(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
=======
    assert 0 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 2 == installer.executor.removals_count


def test_run_install_with_optional_group_selected(
    installer, locker, repo, package, installed
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    _configure_run_install_dev(
        locker, repo, package, installed, with_optional_group=True
    )

    installer.with_groups(["dev"])
    installer.run()

<<<<<<< HEAD
    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0
=======
    assert 0 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)


@pytest.mark.parametrize(
    "managed_reserved_package_names",
<<<<<<< HEAD
    itertools.chain(
        [()],
        itertools.permutations(RESERVED_PACKAGES, 1),
        itertools.permutations(RESERVED_PACKAGES, 2),
        [RESERVED_PACKAGES],
    ),
)
def test_run_install_with_synchronization(
    managed_reserved_package_names: Tuple[str, ...],
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
=======
    [
        i
        for i in itertools.chain(
            [tuple()],
            itertools.permutations(RESERVED_PACKAGES, 1),
            itertools.permutations(RESERVED_PACKAGES, 2),
            [RESERVED_PACKAGES],
        )
    ],
)
def test_run_install_with_synchronization(
    managed_reserved_package_names, installer, locker, repo, package, installed
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {pkg.name: [] for pkg in locked_packages},
            },
        }
    )

    installer.requires_synchronization(True)
    installer.run()

<<<<<<< HEAD
    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
=======
    assert 0 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    assert 2 + len(managed_reserved_packages) == installer.executor.removals_count

    expected_removals = {
        package_b.name,
        package_c.name,
        *managed_reserved_package_names,
    }

<<<<<<< HEAD
    assert expected_removals == {r.name for r in installer.executor.removals}


def test_run_whitelist_add(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
=======
    assert expected_removals == set(r.name for r in installer.executor.removals)


def test_run_whitelist_add(installer, locker, repo, package):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {"A": []},
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


<<<<<<< HEAD
def test_run_whitelist_remove(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
):
=======
def test_run_whitelist_remove(installer, locker, repo, package, installed):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {"A": [], "B": []},
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
<<<<<<< HEAD
    assert installer.executor.installations_count == 1
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 1


def test_add_with_sub_dependencies(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
=======
    assert 1 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 1 == installer.executor.removals_count


def test_add_with_sub_dependencies(installer, locker, repo, package):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_run_with_python_versions(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
=======
def test_run_with_python_versions(installer, locker, repo, package):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
<<<<<<< HEAD
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
=======
    installer, locker, repo, package
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
<<<<<<< HEAD
    assert installer.executor.installations_count == 2
    assert installer.executor.installations[0].name == "d"
    assert installer.executor.installations[1].name == "c"


def test_run_with_optional_and_platform_restricted_dependencies(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    mocker: "MockerFixture",
=======
    assert 2 == installer.executor.installations_count
    assert "d" == installer.executor.installations[0].name
    assert "c" == installer.executor.installations[1].name


def test_run_with_optional_and_platform_restricted_dependencies(
    installer, locker, repo, package, mocker
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
<<<<<<< HEAD
    assert installer.executor.installations_count == 2
    assert installer.executor.installations[0].name == "d"
    assert installer.executor.installations[1].name == "c"


def test_run_with_dependencies_extras(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
=======
    assert 2 == installer.executor.installations_count
    assert "d" == installer.executor.installations[0].name
    assert "c" == installer.executor.installations[1].name


def test_run_with_dependencies_extras(installer, locker, repo, package):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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


<<<<<<< HEAD
def test_run_with_dependencies_nested_extras(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
=======
def test_run_with_dependencies_nested_extras(installer, locker, repo, package):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")

    dependency_c = Factory.create_dependency("C", {"version": "^1.0", "optional": True})
    dependency_b = Factory.create_dependency(
        "B", {"version": "^1.0", "optional": True, "extras": ["C"]}
    )
    dependency_a = Factory.create_dependency("A", {"version": "^1.0", "extras": ["B"]})

    package_b.extras = {"C": [dependency_c]}
    package_b.add_dependency(dependency_c)

    package_a.add_dependency(dependency_b)
    package_a.extras = {"B": [dependency_b]}

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    package.add_dependency(dependency_a)

    installer.run()
    expected = fixture("with-dependencies-nested-extras")

    assert locker.written_data == expected


<<<<<<< HEAD
def test_run_does_not_install_extras_if_not_requested(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
=======
def test_run_does_not_install_extras_if_not_requested(installer, locker, repo, package):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
<<<<<<< HEAD
    assert installer.executor.installations_count == 3  # A, B, C


def test_run_installs_extras_if_requested(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
=======
    assert 3 == installer.executor.installations_count  # A, B, C


def test_run_installs_extras_if_requested(installer, locker, repo, package):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
<<<<<<< HEAD
    assert installer.executor.installations_count == 4  # A, B, C, D


def test_run_installs_extras_with_deps_if_requested(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
=======
    assert 4 == installer.executor.installations_count  # A, B, C, D


def test_run_installs_extras_with_deps_if_requested(installer, locker, repo, package):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
<<<<<<< HEAD
    assert installer.executor.installations_count == 4  # A, B, C, D


def test_run_installs_extras_with_deps_if_requested_locked(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
=======
    assert 4 == installer.executor.installations_count  # A, B, C, D


def test_run_installs_extras_with_deps_if_requested_locked(
    installer, locker, repo, package
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
<<<<<<< HEAD
    assert installer.executor.installations_count == 4  # A, B, C, D


def test_installer_with_pypi_repository(
    package: ProjectPackage,
    locker: Locker,
    installed: CustomInstalledRepository,
    config: "Config",
):
=======
    assert 4 == installer.executor.installations_count  # A, B, C, D


def test_installer_with_pypi_repository(package, locker, installed, config):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    pool = Pool()
    pool.add_repository(MockRepository())

    installer = Installer(
        NullIO(), NullEnv(), package, locker, pool, config, installed=installed
    )

    package.add_dependency(Factory.create_dependency("pytest", "^3.5", groups=["dev"]))
    installer.run()

    expected = fixture("with-pypi-repository")
    assert not DeepDiff(expected, locker.written_data, ignore_order=True)


<<<<<<< HEAD
def test_run_installs_with_local_file(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: "FixtureDirGetter",
):
=======
def test_run_installs_with_local_file(installer, locker, repo, package, fixture_dir):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    file_path = fixture_dir("distributions/demo-0.1.0-py2.py3-none-any.whl")
    package.add_dependency(Factory.create_dependency("demo", {"file": str(file_path)}))

    repo.add_package(get_package("pendulum", "1.4.4"))

    installer.run()

    expected = fixture("with-file-dependency")

    assert locker.written_data == expected
<<<<<<< HEAD
    assert installer.executor.installations_count == 2


def test_run_installs_wheel_with_no_requires_dist(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    fixture_dir: "FixtureDirGetter",
=======
    assert 2 == installer.executor.installations_count


def test_run_installs_wheel_with_no_requires_dist(
    installer, locker, repo, package, fixture_dir
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    file_path = fixture_dir(
        "wheel_with_no_requires_dist/demo-0.1.0-py2.py3-none-any.whl"
    )
    package.add_dependency(Factory.create_dependency("demo", {"file": str(file_path)}))

    installer.run()

    expected = fixture("with-wheel-dependency-no-requires-dist")

    assert locker.written_data == expected

<<<<<<< HEAD
    assert installer.executor.installations_count == 1


def test_run_installs_with_local_poetry_directory_and_extras(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    tmpdir: Path,
    fixture_dir: "FixtureDirGetter",
=======
    assert 1 == installer.executor.installations_count


def test_run_installs_with_local_poetry_directory_and_extras(
    installer, locker, repo, package, tmpdir, fixture_dir
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    file_path = fixture_dir("project_with_extras")
    package.add_dependency(
        Factory.create_dependency(
            "project-with-extras", {"path": str(file_path), "extras": ["extras_a"]}
        )
    )

    repo.add_package(get_package("pendulum", "1.4.4"))

    installer.run()

    expected = fixture("with-directory-dependency-poetry")
    assert locker.written_data == expected

<<<<<<< HEAD
    assert installer.executor.installations_count == 2


def test_run_installs_with_local_poetry_directory_transitive(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    tmpdir: Path,
    fixture_dir: "FixtureDirGetter",
=======
    assert 2 == installer.executor.installations_count


def test_run_installs_with_local_poetry_directory_transitive(
    installer, locker, repo, package, tmpdir, fixture_dir
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

<<<<<<< HEAD
    assert installer.executor.installations_count == 6


def test_run_installs_with_local_poetry_file_transitive(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    tmpdir: str,
    fixture_dir: "FixtureDirGetter",
=======
    assert 6 == installer.executor.installations_count


def test_run_installs_with_local_poetry_file_transitive(
    installer, locker, repo, package, tmpdir, fixture_dir
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

<<<<<<< HEAD
    assert installer.executor.installations_count == 4


def test_run_installs_with_local_setuptools_directory(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    tmpdir: Path,
    fixture_dir: "FixtureDirGetter",
=======
    assert 4 == installer.executor.installations_count


def test_run_installs_with_local_setuptools_directory(
    installer, locker, repo, package, tmpdir, fixture_dir
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    file_path = fixture_dir("project_with_setup/")
    package.add_dependency(
        Factory.create_dependency("project-with-setup", {"path": str(file_path)})
    )

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cachy", "0.2.0"))

    installer.run()

    expected = fixture("with-directory-dependency-setuptools")

    assert locker.written_data == expected
<<<<<<< HEAD
    assert installer.executor.installations_count == 3


def test_run_with_prereleases(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
=======
    assert 3 == installer.executor.installations_count


def test_run_with_prereleases(installer, locker, repo, package):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {"A": []},
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


<<<<<<< HEAD
def test_run_changes_category_if_needed(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
=======
def test_run_changes_category_if_needed(installer, locker, repo, package):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {"A": []},
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


<<<<<<< HEAD
def test_run_update_all_with_lock(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
=======
def test_run_update_all_with_lock(installer, locker, repo, package):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {"A": []},
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


<<<<<<< HEAD
def test_run_update_with_locked_extras(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
=======
def test_run_update_with_locked_extras(installer, locker, repo, package):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {"A": [], "B": [], "C": []},
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
<<<<<<< HEAD
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
=======
    installer, locker, repo, package
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
<<<<<<< HEAD
    assert installer.executor.installations_count == 3
=======
    assert 3 == installer.executor.installations_count
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    assert installs[0] == package_c12
    assert installs[1] == package_b10
    assert installs[2] == package_a

<<<<<<< HEAD
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_run_install_duplicate_dependencies_different_constraints_with_lock(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
=======
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_run_install_duplicate_dependencies_different_constraints_with_lock(
    installer, locker, repo, package
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {"A": [], "B": [], "C": []},
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

<<<<<<< HEAD
    assert installer.executor.installations_count == 3
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_run_update_uninstalls_after_removal_transient_dependency(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
=======
    assert 3 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_run_update_uninstalls_after_removal_transient_dependency(
    installer, locker, repo, package, installed
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {"A": [], "B": []},
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

<<<<<<< HEAD
    assert installer.executor.installations_count == 0
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 1


def test_run_install_duplicate_dependencies_different_constraints_with_lock_update(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
=======
    assert 0 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 1 == installer.executor.removals_count


def test_run_install_duplicate_dependencies_different_constraints_with_lock_update(
    installer, locker, repo, package, installed
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {"A": [], "B": [], "C": []},
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

<<<<<<< HEAD
    assert installer.executor.installations_count == 2
    assert installer.executor.updates_count == 1
    assert installer.executor.removals_count == 0
=======
    assert 2 == installer.executor.installations_count
    assert 1 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)


@pytest.mark.skip(
    "This is not working at the moment due to limitations in the resolver"
)
def test_installer_test_solver_finds_compatible_package_for_dependency_python_not_fully_compatible_with_package_python(
<<<<<<< HEAD
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
=======
    installer, locker, repo, package, installed
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
<<<<<<< HEAD
    assert installer.executor.installations_count == 1


def test_installer_required_extras_should_not_be_removed_when_updating_single_dependency(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    env: NullEnv,
    pool: Pool,
    config: "Config",
=======

    if sys.version_info >= (3, 5, 0):
        assert 1 == installer.executor.installations_count
    else:
        assert 0 == installer.executor.installations_count


def test_installer_required_extras_should_not_be_removed_when_updating_single_dependency(
    installer, locker, repo, package, installed, env, pool, config
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

<<<<<<< HEAD
    assert installer.executor.installations_count == 3
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0
=======
    assert 3 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

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

<<<<<<< HEAD
    assert installer.executor.installations_count == 1
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_installer_required_extras_should_not_be_removed_when_updating_single_dependency_pypi_repository(
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    env: NullEnv,
    mocker: "MockerFixture",
    config: "Config",
=======
    assert 1 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_installer_required_extras_should_not_be_removed_when_updating_single_dependency_pypi_repository(
    locker, repo, package, installed, env, mocker, config
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    mocker.patch("sys.platform", "darwin")

    pool = Pool()
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

<<<<<<< HEAD
    assert installer.executor.installations_count == 3
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0
=======
    assert 3 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

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

<<<<<<< HEAD
    assert installer.executor.installations_count == 7
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_installer_required_extras_should_be_installed(
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    installed: CustomInstalledRepository,
    env: NullEnv,
    config: "Config",
=======
    assert 7 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_installer_required_extras_should_be_installed(
    locker, repo, package, installed, env, config
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    pool = Pool()
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

<<<<<<< HEAD
    assert installer.executor.installations_count == 2
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0
=======
    assert 2 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

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

<<<<<<< HEAD
    assert installer.executor.installations_count == 2
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_update_multiple_times_with_split_dependencies_is_idempotent(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
=======
    assert 2 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_update_multiple_times_with_split_dependencies_is_idempotent(
    installer, locker, repo, package
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {"A": [], "B": []},
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

    assert expected == locker.written_data

    locker.mock_lock_data(locker.written_data)

    installer.update(True)
    installer.run()

    assert expected == locker.written_data

    locker.mock_lock_data(locker.written_data)

    installer.update(True)
    installer.run()

    assert expected == locker.written_data


def test_installer_can_install_dependencies_from_forced_source(
<<<<<<< HEAD
    locker: Locker,
    package: Package,
    installed: CustomInstalledRepository,
    env: NullEnv,
    config: "Config",
=======
    locker, package, installed, env, config
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    package.python_versions = "^3.7"
    package.add_dependency(
        Factory.create_dependency("tomlkit", {"version": "^0.5", "source": "legacy"})
    )

    pool = Pool()
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

<<<<<<< HEAD
    assert installer.executor.installations_count == 1
    assert installer.executor.updates_count == 0
    assert installer.executor.removals_count == 0


def test_run_installs_with_url_file(
    installer: Installer, locker: Locker, repo: Repository, package: ProjectPackage
):
=======
    assert 1 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_run_installs_with_url_file(installer, locker, repo, package):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    url = "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
    package.add_dependency(Factory.create_dependency("demo", {"url": url}))

    repo.add_package(get_package("pendulum", "1.4.4"))

    installer.run()

    expected = fixture("with-url-dependency")

    assert locker.written_data == expected

<<<<<<< HEAD
    assert installer.executor.installations_count == 2


def test_installer_uses_prereleases_if_they_are_compatible(
    installer: Installer, locker: Locker, package: ProjectPackage, repo: Repository
=======
    assert 2 == installer.executor.installations_count


def test_installer_uses_prereleases_if_they_are_compatible(
    installer, locker, package, repo
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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

<<<<<<< HEAD
    assert installer.executor.installations_count == 2


def test_installer_can_handle_old_lock_files(
    locker: Locker,
    package: ProjectPackage,
    repo: Repository,
    installed: CustomInstalledRepository,
    config: "Config",
=======
    assert 2 == installer.executor.installations_count


def test_installer_can_handle_old_lock_files(
    installer, locker, package, repo, installed, config
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
):
    pool = Pool()
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

<<<<<<< HEAD
    assert installer.executor.installations_count == 6
=======
    assert 6 == installer.executor.installations_count
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

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
<<<<<<< HEAD
    assert installer.executor.installations_count == 7
=======
    assert 7 == installer.executor.installations_count
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

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
<<<<<<< HEAD
    assert installer.executor.installations_count == 8


@pytest.mark.parametrize("quiet", [True, False])
def test_run_with_dependencies_quiet(
    installer: Installer,
    locker: Locker,
    repo: Repository,
    package: ProjectPackage,
    quiet: bool,
):
=======
    assert 8 == installer.executor.installations_count


@pytest.mark.parametrize("quiet", [True, False])
def test_run_with_dependencies_quiet(installer, locker, repo, package, quiet):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
<<<<<<< HEAD
    installer: Installer, locker: Locker, package: ProjectPackage, repo: Repository
=======
    installer, locker, package, repo
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
                "hashes": {"demo": [], "pendulum": []},
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
