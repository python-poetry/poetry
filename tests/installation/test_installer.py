from __future__ import unicode_literals

import sys

import pytest

from poetry.installation import Installer as BaseInstaller
from poetry.installation.noop_installer import NoopInstaller
from poetry.io import NullIO
from poetry.packages import Locker as BaseLocker
from poetry.packages import ProjectPackage
from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils._compat import Path
from poetry.utils._compat import PY2
from poetry.utils.toml_file import TomlFile
from poetry.utils.env import NullEnv

from tests.helpers import get_dependency
from tests.helpers import get_package
from tests.repositories.test_pypi_repository import MockRepository


class Installer(BaseInstaller):
    def _get_installer(self):
        return NoopInstaller()


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
def installer(package, pool, locker, env, installed):
    return Installer(NullIO(), env, package, locker, pool, installed=installed)


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

    installs = installer.installer.installs
    assert len(installs) == 0

    updates = installer.installer.updates
    assert len(updates) == 0

    removals = installer.installer.removals
    assert len(removals) == 1


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

    installs = installer.installer.installs
    assert len(installs) == 0

    updates = installer.installer.updates
    assert len(updates) == 0

    removals = installer.installer.removals
    assert len(removals) == 1


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


def test_run_whitelist_remove(installer, locker, repo, package):
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

    package.add_dependency("A", "~1.0")

    installer.update(True)
    installer.whitelist(["B"])

    installer.run()
    expected = fixture("remove")

    assert locker.written_data == expected


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

    installer = installer.installer
    # We should only have 2 installs:
    # C,D since python version is not compatible
    # with B's python constraint and A is optional
    assert len(installer.installs) == 2
    assert installer.installs[0].name == "d"
    assert installer.installs[1].name == "c"


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

    installer = installer.installer
    # We should only have 2 installs:
    # C,D since the mocked python version is not compatible
    # with B's python constraint and A is optional
    assert len(installer.installs) == 2
    assert installer.installs[0].name == "d"
    assert installer.installs[1].name == "c"


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
    installer = installer.installer
    assert len(installer.installs) == 3  # A, B, C


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
    installer = installer.installer
    assert len(installer.installs) == 4  # A, B, C, D


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
    installer = installer.installer
    assert len(installer.installs) == 4  # A, B, C, D


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
    installer = installer.installer
    assert len(installer.installs) == 4  # A, B, C, D


def test_installer_with_pypi_repository(package, locker, installed):
    pool = Pool()
    pool.add_repository(MockRepository())

    installer = Installer(
        NullIO(), NullEnv(), package, locker, pool, installed=installed
    )

    package.add_dependency("pytest", "^3.5", category="dev")
    installer.run()

    expected = fixture("with-pypi-repository")

    assert locker.written_data == expected


def test_run_installs_with_local_file(installer, locker, repo, package):
    file_path = Path("tests/fixtures/distributions/demo-0.1.0-py2.py3-none-any.whl")
    package.add_dependency("demo", {"file": str(file_path)})

    repo.add_package(get_package("pendulum", "1.4.4"))

    installer.run()

    expected = fixture("with-file-dependency")

    assert locker.written_data == expected

    assert len(installer.installer.installs) == 2


def test_run_installs_with_local_poetry_directory_and_extras(
    installer, locker, repo, package, tmpdir
):
    file_path = Path("tests/fixtures/project_with_extras")
    package.add_dependency(
        "project-with-extras", {"path": str(file_path), "extras": ["extras_a"]}
    )

    repo.add_package(get_package("pendulum", "1.4.4"))

    installer.run()

    expected = fixture("with-directory-dependency-poetry")

    assert locker.written_data == expected

    assert len(installer.installer.installs) == 2


def test_run_installs_with_local_poetry_directory_transitive(
    installer, locker, repo, package, tmpdir
):
    file_path = Path(
        "tests/fixtures/directory/project_with_transitive_directory_dependencies/"
    )
    package.add_dependency(
        "project-with-transitive-directory-dependencies", {"path": str(file_path)}
    )

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cachy", "0.2.0"))

    installer.run()

    expected = fixture("with-directory-dependency-poetry-transitive")

    assert locker.written_data == expected

    assert len(installer.installer.installs) == 2


def test_run_installs_with_local_poetry_file_transitive(
    installer, locker, repo, package, tmpdir
):
    file_path = Path(
        "tests/fixtures/directory/project_with_transitive_file_dependencies/"
    )
    package.add_dependency(
        "project-with-transitive-file-dependencies", {"path": str(file_path)}
    )

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cachy", "0.2.0"))

    installer.run()

    expected = fixture("with-file-dependency-transitive")

    assert locker.written_data == expected

    assert len(installer.installer.installs) == 3


def test_run_installs_with_local_setuptools_directory(
    installer, locker, repo, package, tmpdir
):
    file_path = Path("tests/fixtures/project_with_setup/")
    package.add_dependency("my-package", {"path": str(file_path)})

    repo.add_package(get_package("pendulum", "1.4.4"))
    repo.add_package(get_package("cachy", "0.2.0"))

    installer.run()

    expected = fixture("with-directory-dependency-setuptools")

    assert locker.written_data == expected

    assert len(installer.installer.installs) == 3


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

    installs = installer.installer.installs
    assert len(installs) == 3
    assert installs[0] == package_c12
    assert installs[1] == package_b10
    assert installs[2] == package_a

    updates = installer.installer.updates
    assert len(updates) == 0
    removals = installer.installer.removals
    assert len(removals) == 0


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

    installs = installer.installer.installs
    assert len(installs) == 3
    updates = installer.installer.updates
    assert len(updates) == 0
    removals = installer.installer.removals
    assert len(removals) == 0


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

    installs = installer.installer.installs
    assert len(installs) == 0
    updates = installer.installer.updates
    assert len(updates) == 0
    removals = installer.installer.removals
    assert len(removals) == 1


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

    installs = installer.installer.installs
    assert len(installs) == 2
    updates = installer.installer.updates
    assert len(updates) == 1
    removals = installer.installer.removals
    assert len(removals) == 0


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

    installs = installer.installer.installs

    if sys.version_info >= (3, 5, 0):
        assert len(installs) == 1
    else:
        assert len(installs) == 0
