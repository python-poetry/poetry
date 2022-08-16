from __future__ import unicode_literals

import sys

import pytest

from clikit.io import NullIO

from poetry.core.packages import ProjectPackage
from poetry.installation import Installer as BaseInstaller
from poetry.installation.executor import Executor as BaseExecutor
from poetry.installation.noop_installer import NoopInstaller
from poetry.packages import Locker as BaseLocker
from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils._compat import PY2
from poetry.utils._compat import Path
from poetry.utils.env import MockEnv
from poetry.utils.env import NullEnv
from poetry.utils.toml_file import TomlFile
from tests.helpers import get_dependency
from tests.helpers import get_package
from tests.repositories.test_legacy_repository import (
    MockRepository as MockLegacyRepository,
)
from tests.repositories.test_pypi_repository import MockRepository


fixtures_dir = Path("tests/fixtures")


class Installer(BaseInstaller):
    def _get_installer(self):
        return NoopInstaller()


class Executor(BaseExecutor):
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
        return 0


class CustomInstalledRepository(InstalledRepository):
    @classmethod
    def load(cls, env):
        return cls()


class Locker(BaseLocker):
    def __init__(self):
        self._written_data = None
        self._locked = False
        self._content_hash = self._get_content_hash()

    @property
    def written_data(self):
        return self._written_data

    def locked(self, is_locked=True):
        self._locked = is_locked

        return self

    def mock_lock_data(self, data):
        self._lock_data = data

    def is_locked(self):
        return self._locked

    def is_fresh(self):
        return True

    def _get_content_hash(self):
        return "123456789"

    def _write_lock_data(self, data):
        for package in data["package"]:
            python_versions = str(package["python-versions"])
            if PY2:
                python_versions = python_versions.decode()
                if "requirements" in package:
                    requirements = {}
                    for key, value in package["requirements"].items():
                        requirements[key.decode()] = value.decode()

                    package["requirements"] = requirements

            package["python-versions"] = python_versions

        self._written_data = data
        self._lock_data = data


@pytest.fixture()
def package():
    p = ProjectPackage("root", "1.0")
    p.root_dir = Path.cwd()

    return p


@pytest.fixture()
def repo():
    return Repository()


@pytest.fixture()
def pool(repo):
    pool = Pool()
    pool.add_repository(repo)

    return pool


@pytest.fixture()
def installed():
    return CustomInstalledRepository()


@pytest.fixture()
def locker():
    return Locker()


@pytest.fixture()
def env():
    return NullEnv()


@pytest.fixture()
def installer(package, pool, locker, env, installed, config):
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


def fixture(name):
    file = TomlFile(Path(__file__).parent / "fixtures" / "{}.test".format(name))

    return file.read()


def test_run_no_dependencies(installer, locker):
    installer.run()
    expected = fixture("no-dependencies")

    assert locker.written_data == expected


def test_run_with_dependencies(installer, locker, repo, package):
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    repo.add_package(package_a)
    repo.add_package(package_b)

    package.add_dependency("A", "~1.0")
    package.add_dependency("B", "^1.0")

    installer.run()
    expected = fixture("with-dependencies")

    assert locker.written_data == expected


def test_run_update_after_removing_dependencies(
    installer, locker, repo, package, installed
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

    package.add_dependency("A", "~1.0")
    package.add_dependency("B", "~1.1")

    installer.update(True)
    installer.run()
    expected = fixture("with-dependencies")

    assert locker.written_data == expected

    assert 0 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 1 == installer.executor.removals_count


def test_run_install_no_dev(installer, locker, repo, package, installed):
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

    package.add_dependency("A", "~1.0")
    package.add_dependency("B", "~1.1")
    package.add_dependency("C", "~1.2", category="dev")

    installer.dev_mode(False)
    installer.run()

    assert 0 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 1 == installer.executor.removals_count


def test_run_install_remove_untracked(installer, locker, repo, package, installed):
    locker.locked(True)
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "a",
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
                "hashes": {"a": []},
            },
        }
    )
    package_a = get_package("a", "1.0")
    package_b = get_package("b", "1.1")
    package_c = get_package("c", "1.2")
    package_pip = get_package("pip", "20.0.0")
    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_pip)

    installed.add_package(package_a)
    installed.add_package(package_b)
    installed.add_package(package_c)
    installed.add_package(package_pip)  # Always required and never removed.
    installed.add_package(package)  # Root package never removed.

    package.add_dependency("A", "~1.0")

    installer.dev_mode(True).remove_untracked(True)
    installer.run()

    assert 0 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 2 == installer.executor.removals_count
    assert {"b", "c"} == set(r.name for r in installer.executor.removals)


def test_run_whitelist_add(installer, locker, repo, package):
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

    package.add_dependency("A", "~1.0")
    package.add_dependency("B", "^1.0")

    installer.update(True)
    installer.whitelist(["B"])

    installer.run()
    expected = fixture("with-dependencies")

    assert locker.written_data == expected


def test_run_whitelist_remove(installer, locker, repo, package, installed):
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

    package.add_dependency("A", "~1.0")

    installer.update(True)
    installer.whitelist(["B"])

    installer.run()
    expected = fixture("remove")

    assert locker.written_data == expected
    assert 1 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 1 == installer.executor.removals_count


def test_add_with_sub_dependencies(installer, locker, repo, package):
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    package_c = get_package("C", "1.2")
    package_d = get_package("D", "1.3")
    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    package.add_dependency("A", "~1.0")
    package.add_dependency("B", "^1.0")

    package_a.add_dependency("D", "^1.0")
    package_b.add_dependency("C", "~1.2")

    installer.run()
    expected = fixture("with-sub-dependencies")

    assert locker.written_data == expected


def test_run_with_python_versions(installer, locker, repo, package):
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

    package.add_dependency("A", "~1.0")
    package.add_dependency("B", "^1.0")
    package.add_dependency("C", "^1.0")

    installer.run()
    expected = fixture("with-python-versions")

    assert locker.written_data == expected


def test_run_with_optional_and_python_restricted_dependencies(
    installer, locker, repo, package
):
    package.python_versions = "~2.7 || ^3.4"

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    package_c12 = get_package("C", "1.2")
    package_c13 = get_package("C", "1.3")
    package_d = get_package("D", "1.4")
    package_c13.add_dependency("D", "^1.2")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c12)
    repo.add_package(package_c13)
    repo.add_package(package_d)

    package.extras = {"foo": [get_dependency("A", "~1.0")]}
    package.add_dependency("A", {"version": "~1.0", "optional": True})
    package.add_dependency("B", {"version": "^1.0", "python": "~2.4"})
    package.add_dependency("C", {"version": "^1.0", "python": "~2.7 || ^3.4"})

    installer.run()
    expected = fixture("with-optional-dependencies")

    assert locker.written_data == expected

    # We should only have 2 installs:
    # C,D since python version is not compatible
    # with B's python constraint and A is optional
    assert 2 == installer.executor.installations_count
    assert "d" == installer.executor.installations[0].name
    assert "c" == installer.executor.installations[1].name


def test_run_with_optional_and_platform_restricted_dependencies(
    installer, locker, repo, package, mocker
):
    mocker.patch("sys.platform", "darwin")

    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.1")
    package_c12 = get_package("C", "1.2")
    package_c13 = get_package("C", "1.3")
    package_d = get_package("D", "1.4")
    package_c13.add_dependency("D", "^1.2")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c12)
    repo.add_package(package_c13)
    repo.add_package(package_d)

    package.extras = {"foo": [get_dependency("A", "~1.0")]}
    package.add_dependency("A", {"version": "~1.0", "optional": True})
    package.add_dependency("B", {"version": "^1.0", "platform": "custom"})
    package.add_dependency("C", {"version": "^1.0", "platform": "darwin"})

    installer.run()
    expected = fixture("with-platform-dependencies")

    assert locker.written_data == expected

    # We should only have 2 installs:
    # C,D since the mocked python version is not compatible
    # with B's python constraint and A is optional
    assert 2 == installer.executor.installations_count
    assert "d" == installer.executor.installations[0].name
    assert "c" == installer.executor.installations[1].name


def test_run_with_dependencies_extras(installer, locker, repo, package):
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")

    package_b.extras = {"foo": [get_dependency("C", "^1.0")]}
    package_b.add_dependency("C", {"version": "^1.0", "optional": True})

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)

    package.add_dependency("A", "^1.0")
    package.add_dependency("B", {"version": "^1.0", "extras": ["foo"]})

    installer.run()
    expected = fixture("with-dependencies-extras")

    assert locker.written_data == expected


def test_run_does_not_install_extras_if_not_requested(installer, locker, repo, package):
    package.extras["foo"] = [get_dependency("D")]
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_d = get_package("D", "1.1")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    package.add_dependency("A", "^1.0")
    package.add_dependency("B", "^1.0")
    package.add_dependency("C", "^1.0")
    package.add_dependency("D", {"version": "^1.0", "optional": True})

    installer.run()
    expected = fixture("extras")

    # Extras are pinned in lock
    assert locker.written_data == expected

    # But should not be installed
    assert 3 == installer.executor.installations_count  # A, B, C


def test_run_installs_extras_if_requested(installer, locker, repo, package):
    package.extras["foo"] = [get_dependency("D")]
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_d = get_package("D", "1.1")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    package.add_dependency("A", "^1.0")
    package.add_dependency("B", "^1.0")
    package.add_dependency("C", "^1.0")
    package.add_dependency("D", {"version": "^1.0", "optional": True})

    installer.extras(["foo"])
    installer.run()
    expected = fixture("extras")

    # Extras are pinned in lock
    assert locker.written_data == expected

    # But should not be installed
    assert 4 == installer.executor.installations_count  # A, B, C, D


def test_run_installs_extras_with_deps_if_requested(installer, locker, repo, package):
    package.extras["foo"] = [get_dependency("C")]
    package_a = get_package("A", "1.0")
    package_b = get_package("B", "1.0")
    package_c = get_package("C", "1.0")
    package_d = get_package("D", "1.1")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    package.add_dependency("A", "^1.0")
    package.add_dependency("B", "^1.0")
    package.add_dependency("C", {"version": "^1.0", "optional": True})

    package_c.add_dependency("D", "^1.0")

    installer.extras(["foo"])
    installer.run()
    expected = fixture("extras-with-dependencies")

    # Extras are pinned in lock
    assert locker.written_data == expected

    # But should not be installed
    assert 4 == installer.executor.installations_count  # A, B, C, D


def test_run_installs_extras_with_deps_if_requested_locked(
    installer, locker, repo, package
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

    package.add_dependency("A", "^1.0")
    package.add_dependency("B", "^1.0")
    package.add_dependency("C", {"version": "^1.0", "optional": True})

    package_c.add_dependency("D", "^1.0")

    installer.extras(["foo"])
    installer.run()

    # But should not be installed
    assert 4 == installer.executor.installations_count  # A, B, C, D


def test_installer_with_pypi_repository(package, locker, installed, config):
    pool = Pool()
    pool.add_repository(MockRepository())

    installer = Installer(
        NullIO(), NullEnv(), package, locker, pool, config, installed=installed
    )

    package.add_dependency("pytest", "^3.5", category="dev")
    installer.run()

    expected = fixture("with-pypi-repository")

    assert locker.written_data == expected


def test_run_installs_with_local_file(installer, locker, repo, package):
    file_path = fixtures_dir / "distributions/demo-0.1.0-py2.py3-none-any.whl"
    package.add_dependency("demo", {"file": str(file_path)})

    repo.add_package(get_package("pendulum", "1.4.4"))

    installer.run()

    expected = fixture("with-file-dependency")

    assert locker.written_data == expected

    assert 2 == installer.executor.installations_count


def test_run_installs_wheel_with_no_requires_dist(installer, locker, repo, package):
    file_path = (
        fixtures_dir / "wheel_with_no_requires_dist/demo-0.1.0-py2.py3-none-any.whl"
    )
    package.add_dependency("demo", {"file": str(file_path)})

    installer.run()

    expected = fixture("with-wheel-dependency-no-requires-dist")

    assert locker.written_data == expected

    assert 1 == installer.executor.installations_count


def test_run_installs_with_local_poetry_directory_and_extras(
    installer, locker, repo, package, tmpdir
):
    file_path = fixtures_dir / "project_with_extras"
    package.add_dependency(
        "project-with-extras", {"path": str(file_path), "extras": ["extras_a"]}
    )

    repo.add_package(get_package("pendulum", "1.4.4"))

    installer.run()

    expected = fixture("with-directory-dependency-poetry")

    assert locker.written_data == expected

    assert 2 == installer.executor.installations_count


def test_run_installs_with_local_poetry_directory_transitive(
    installer, locker, repo, package, tmpdir
):
    package.root_dir = fixtures_dir.joinpath("directory")
    directory = fixtures_dir.joinpath("directory").joinpath(
        "project_with_transitive_directory_dependencies"
    )
    package.add_dependency(
        "project-with-transitive-directory-dependencies",
        {"path": str(directory.relative_to(fixtures_dir.joinpath("directory")))},
    )

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cachy", "0.2.0"))

    installer.run()

    expected = fixture("with-directory-dependency-poetry-transitive")

    assert locker.written_data == expected

    assert 6 == installer.executor.installations_count


def test_run_installs_with_local_poetry_file_transitive(
    installer, locker, repo, package, tmpdir
):
    package.root_dir = fixtures_dir.joinpath("directory")
    directory = fixtures_dir.joinpath("directory").joinpath(
        "project_with_transitive_file_dependencies"
    )
    package.add_dependency(
        "project-with-transitive-file-dependencies",
        {"path": str(directory.relative_to(fixtures_dir.joinpath("directory")))},
    )

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cachy", "0.2.0"))

    installer.run()

    expected = fixture("with-file-dependency-transitive")

    assert locker.written_data == expected

    assert 4 == installer.executor.installations_count


def test_run_installs_with_local_setuptools_directory(
    installer, locker, repo, package, tmpdir
):
    file_path = fixtures_dir / "project_with_setup/"
    package.add_dependency("my-package", {"path": str(file_path)})

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cachy", "0.2.0"))

    installer.run()

    expected = fixture("with-directory-dependency-setuptools")

    assert locker.written_data == expected

    assert 3 == installer.executor.installations_count


def test_run_with_prereleases(installer, locker, repo, package):
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

    package.add_dependency("A", {"version": "*", "allows-prereleases": True})
    package.add_dependency("B", "^1.1")

    installer.update(True)
    installer.whitelist({"B": "^1.1"})

    installer.run()
    expected = fixture("with-prereleases")

    assert locker.written_data == expected


def test_run_changes_category_if_needed(installer, locker, repo, package):
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
    package_b.add_dependency("A", "^1.0")
    repo.add_package(package_a)
    repo.add_package(package_b)

    package.add_dependency("A", {"version": "^1.0", "optional": True}, category="dev")
    package.add_dependency("B", "^1.1")

    installer.update(True)
    installer.whitelist(["B"])

    installer.run()
    expected = fixture("with-category-change")

    assert locker.written_data == expected


def test_run_update_all_with_lock(installer, locker, repo, package):
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

    package.add_dependency("A")

    installer.update(True)

    installer.run()
    expected = fixture("update-with-lock")

    assert locker.written_data == expected


def test_run_update_with_locked_extras(installer, locker, repo, package):
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
    package_a.requires.append(b_dependency)
    package_a.requires.append(c_dependency)

    repo.add_package(package_a)
    repo.add_package(get_package("B", "1.0"))
    repo.add_package(get_package("C", "1.1"))
    repo.add_package(get_package("D", "1.1"))

    package.add_dependency("A", {"version": "^1.0", "extras": ["foo"]})
    package.add_dependency("D", "^1.0")

    installer.update(True)
    installer.whitelist("D")

    installer.run()
    expected = fixture("update-with-locked-extras")

    assert locker.written_data == expected


def test_run_install_duplicate_dependencies_different_constraints(
    installer, locker, repo, package
):
    package.add_dependency("A")

    package_a = get_package("A", "1.0")
    package_a.add_dependency("B", {"version": "^1.0", "python": "<4.0"})
    package_a.add_dependency("B", {"version": "^2.0", "python": ">=4.0"})

    package_b10 = get_package("B", "1.0")
    package_b20 = get_package("B", "2.0")
    package_b10.add_dependency("C", "1.2")
    package_b20.add_dependency("C", "1.5")

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
    assert 3 == installer.executor.installations_count
    assert installs[0] == package_c12
    assert installs[1] == package_b10
    assert installs[2] == package_a

    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_run_install_duplicate_dependencies_different_constraints_with_lock(
    installer, locker, repo, package
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
    package.add_dependency("A")

    package_a = get_package("A", "1.0")
    package_a.add_dependency("B", {"version": "^1.0", "python": "<4.0"})
    package_a.add_dependency("B", {"version": "^2.0", "python": ">=4.0"})

    package_b10 = get_package("B", "1.0")
    package_b20 = get_package("B", "2.0")
    package_b10.add_dependency("C", "1.2")
    package_b20.add_dependency("C", "1.5")

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

    assert 3 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_run_update_uninstalls_after_removal_transient_dependency(
    installer, locker, repo, package, installed
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
    package.add_dependency("A")

    package_a = get_package("A", "1.0")
    package_a.add_dependency("B", {"version": "^1.0", "python": "<2.0"})

    package_b10 = get_package("B", "1.0")

    repo.add_package(package_a)
    repo.add_package(package_b10)

    installed.add_package(get_package("A", "1.0"))
    installed.add_package(get_package("B", "1.0"))

    installer.update(True)
    installer.run()

    assert 0 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 1 == installer.executor.removals_count


def test_run_install_duplicate_dependencies_different_constraints_with_lock_update(
    installer, locker, repo, package, installed
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
    package.add_dependency("A")

    package_a = get_package("A", "1.1")
    package_a.add_dependency("B", "^2.0")

    package_b10 = get_package("B", "1.0")
    package_b20 = get_package("B", "2.0")
    package_b10.add_dependency("C", "1.2")
    package_b20.add_dependency("C", "1.5")

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

    assert 2 == installer.executor.installations_count
    assert 1 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


@pytest.mark.skip(
    "This is not working at the moment due to limitations in the resolver"
)
def test_installer_test_solver_finds_compatible_package_for_dependency_python_not_fully_compatible_with_package_python(
    installer, locker, repo, package, installed
):
    package.python_versions = "~2.7 || ^3.4"
    package.add_dependency("A", {"version": "^1.0", "python": "^3.5"})

    package_a101 = get_package("A", "1.0.1")
    package_a101.python_versions = ">=3.6"

    package_a100 = get_package("A", "1.0.0")
    package_a100.python_versions = ">=3.5"

    repo.add_package(package_a100)
    repo.add_package(package_a101)

    installer.run()

    expected = fixture("with-conditional-dependency")
    assert locker.written_data == expected

    if sys.version_info >= (3, 5, 0):
        assert 1 == installer.executor.installations_count
    else:
        assert 0 == installer.executor.installations_count


def test_installer_required_extras_should_not_be_removed_when_updating_single_dependency(
    installer, locker, repo, package, installed, env, pool, config
):
    package.add_dependency("A", {"version": "^1.0"})

    package_a = get_package("A", "1.0.0")
    package_a.add_dependency("B", {"version": "^1.0", "extras": ["foo"]})

    package_b = get_package("B", "1.0.0")
    package_b.add_dependency("C", {"version": "^1.0", "optional": True})
    package_b.extras = {"foo": [get_dependency("C")]}

    package_c = get_package("C", "1.0.0")
    package_d = get_package("D", "1.0.0")

    repo.add_package(package_a)
    repo.add_package(package_b)
    repo.add_package(package_c)
    repo.add_package(package_d)

    installer.update(True)
    installer.run()

    assert 3 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count

    package.add_dependency("D", "^1.0")
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

    assert 1 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_installer_required_extras_should_not_be_removed_when_updating_single_dependency_pypi_repository(
    locker, repo, package, installed, env, mocker, config
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

    package.add_dependency("poetry", {"version": "^0.12.0"})

    installer.update(True)
    installer.run()

    assert 3 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count

    package.add_dependency("pytest", "^3.5")

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

    assert (6 if not PY2 else 7) == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_installer_required_extras_should_be_installed(
    locker, repo, package, installed, env, config
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
        "cachecontrol", {"version": "^0.12.5", "extras": ["filecache"]}
    )

    installer.update(True)
    installer.run()

    assert 2 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count

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

    assert 2 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_update_multiple_times_with_split_dependencies_is_idempotent(
    installer, locker, repo, package
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
    package.add_dependency("A", "^1.0")

    a10 = get_package("A", "1.0")
    a11 = get_package("A", "1.1")
    a11.add_dependency("B", ">=1.0.1")
    a11.add_dependency("C", {"version": "^1.0", "python": "~2.7"})
    a11.add_dependency("C", {"version": "^2.0", "python": "^3.4"})
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
    locker, package, installed, env, config
):
    package.python_versions = "^3.7"
    package.add_dependency("tomlkit", {"version": "^0.5", "source": "legacy"})

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

    assert 1 == installer.executor.installations_count
    assert 0 == installer.executor.updates_count
    assert 0 == installer.executor.removals_count


def test_run_installs_with_url_file(installer, locker, repo, package):
    url = "https://python-poetry.org/distributions/demo-0.1.0-py2.py3-none-any.whl"
    package.add_dependency("demo", {"url": url})

    repo.add_package(get_package("pendulum", "1.4.4"))

    installer.run()

    expected = fixture("with-url-dependency")

    assert locker.written_data == expected

    assert 2 == installer.executor.installations_count


def test_installer_uses_prereleases_if_they_are_compatible(
    installer, locker, package, repo
):
    package.python_versions = "~2.7 || ^3.4"
    package.add_dependency(
        "prerelease", {"git": "https://github.com/demo/prerelease.git"}
    )

    package_b = get_package("b", "2.0.0")
    package_b.add_dependency("prerelease", ">=0.19")

    repo.add_package(package_b)

    installer.run()

    del installer.installer.installs[:]
    locker.locked(True)
    locker.mock_lock_data(locker.written_data)

    package.add_dependency("b", "^2.0.0")

    installer.whitelist(["b"])
    installer.update(True)
    installer.run()

    assert 2 == installer.executor.installations_count


def test_installer_can_handle_old_lock_files(
    installer, locker, package, repo, installed, config
):
    pool = Pool()
    pool.add_repository(MockRepository())

    package.add_dependency("pytest", "^3.5", category="dev")

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
        executor=Executor(
            MockEnv(),
            pool,
            config,
            NullIO(),
        ),
    )
    installer.use_executor()

    installer.run()

    assert 6 == installer.executor.installations_count

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
    assert 7 == installer.executor.installations_count

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
    assert 8 == installer.executor.installations_count
