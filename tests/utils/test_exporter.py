from __future__ import annotations

import sys

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Iterator

import pytest

from poetry.core.packages.dependency import Dependency
from poetry.core.toml.file import TOMLFile

from poetry.factory import Factory
from poetry.packages import Locker as BaseLocker
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.utils.exporter import Exporter


if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from tests.conftest import Config
    from tests.types import FixtureDirGetter


class Locker(BaseLocker):
    def __init__(self) -> None:
        self._lock = TOMLFile(Path.cwd().joinpath("poetry.lock"))
        self._locked = True
        self._content_hash = self._get_content_hash()

    def locked(self, is_locked: bool = True) -> Locker:
        self._locked = is_locked

        return self

    def mock_lock_data(self, data: dict[str, Any]):
        self._lock_data = data

    def is_locked(self) -> bool:
        return self._locked

    def is_fresh(self) -> bool:
        return True

    def _get_content_hash(self) -> str:
        return "123456789"


@pytest.fixture
def working_directory() -> Path:
    return Path(__file__).parent.parent.parent


@pytest.fixture(autouse=True)
def mock_path_cwd(
    mocker: MockerFixture, working_directory: Path
) -> Iterator[MockerFixture]:
    yield mocker.patch("pathlib.Path.cwd", return_value=working_directory)


@pytest.fixture()
def locker() -> Locker:
    return Locker()


@pytest.fixture
def poetry(fixture_dir: FixtureDirGetter, locker: Locker) -> Poetry:
    p = Factory().create_poetry(fixture_dir("sample_project"))
    p._locker = locker

    return p


def set_package_requires(poetry: Poetry, skip: set[str] | None = None) -> None:
    skip = skip or set()
    packages = poetry.locker.locked_repository(with_dev_reqs=True).packages
    package = poetry.package.with_dependency_groups([], only=True)
    for pkg in packages:
        if pkg.name not in skip:
            package.add_dependency(pkg.to_dependency())

    poetry._package = package


def test_exporter_can_export_requirements_txt_with_standard_packages(
    tmp_dir: str, poetry: Poetry
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": [], "bar": []},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
bar==4.5.6 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
foo==1.2.3 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
"""

    assert content == expected


def test_exporter_can_export_requirements_txt_with_standard_packages_and_markers(
    tmp_dir: str, poetry: Poetry
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "marker": "python_version < '3.7'",
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "marker": "extra =='foo'",
                },
                {
                    "name": "baz",
                    "version": "7.8.9",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "marker": "sys_platform == 'win32'",
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": [], "bar": [], "baz": []},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
bar==4.5.6 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
baz==7.8.9 ;\
 python_version >= "2.7" and python_version < "2.8" and sys_platform == "win32" or\
 python_version >= "3.6" and python_version < "4.0" and sys_platform == "win32"
foo==1.2.3 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "3.7"
"""

    assert content == expected


def test_exporter_can_export_requirements_txt_poetry(tmp_dir: str, poetry: Poetry):
    """Regression test for #3254"""

    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "poetry",
                    "version": "1.1.4",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {"keyring": "*"},
                },
                {
                    "name": "junit-xml",
                    "version": "1.9",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {"six": "*"},
                },
                {
                    "name": "keyring",
                    "version": "21.8.0",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {
                        "SecretStorage": {
                            "version": "*",
                            "markers": "sys_platform == 'linux'",
                        }
                    },
                },
                {
                    "name": "secretstorage",
                    "version": "3.3.0",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {"cryptography": "*"},
                },
                {
                    "name": "cryptography",
                    "version": "3.2",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {"six": "*"},
                },
                {
                    "name": "six",
                    "version": "1.15.0",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {
                    "poetry": [],
                    "keyring": [],
                    "secretstorage": [],
                    "cryptography": [],
                    "six": [],
                    "junit-xml": [],
                },
            },
        }
    )
    set_package_requires(
        poetry, skip={"keyring", "secretstorage", "cryptography", "six"}
    )

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    # The dependency graph:
    # junit-xml 1.9 Creates JUnit XML test result documents that can be read by tools
    # └── six *     such as Jenkins
    # poetry 1.1.4 Python dependency management and packaging made easy.
    # ├── keyring >=21.2.0,<22.0.0
    # │   ├── importlib-metadata >=1
    # │   │   └── zipp >=0.5
    # │   ├── jeepney >=0.4.2
    # │   ├── pywin32-ctypes <0.1.0 || >0.1.0,<0.1.1 || >0.1.1
    # │   └── secretstorage >=3.2 -- On linux only
    # │       ├── cryptography >=2.0
    # │       │   └── six >=1.4.1
    # │       └── jeepney >=0.6 (circular dependency aborted here)
    python27 = 'python_version >= "2.7" and python_version < "2.8"'
    python36 = 'python_version >= "3.6" and python_version < "4.0"'
    linux = 'sys_platform=="linux"'
    expected = {
        "poetry": Dependency.create_from_pep_508(
            f"poetry==1.1.4; {python27} or {python36}"
        ),
        "junit-xml": Dependency.create_from_pep_508(
            f"junit-xml==1.9 ; {python27} or {python36}"
        ),
        "keyring": Dependency.create_from_pep_508(
            f"keyring==21.8.0 ; {python27} or {python36}"
        ),
        "secretstorage": Dependency.create_from_pep_508(
            f"secretstorage==3.3.0 ; {python27} and {linux} or {python36} and {linux}"
        ),
        "cryptography": Dependency.create_from_pep_508(
            f"cryptography==3.2 ; {python27} and {linux} or {python36} and {linux}"
        ),
        "six": Dependency.create_from_pep_508(
            f"six==1.15.0 ; {python27} or {python36} or {python27} and {linux} or"
            f" {python36} and {linux}"
        ),
    }

    for line in content.strip().split("\n"):
        dependency = Dependency.create_from_pep_508(line)
        assert dependency.name in expected
        expected_dependency = expected.pop(dependency.name)
        assert dependency == expected_dependency
        assert dependency.marker == expected_dependency.marker


def test_exporter_can_export_requirements_txt_pyinstaller(tmp_dir: str, poetry: Poetry):
    """Regression test for #3254"""

    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "pyinstaller",
                    "version": "4.0",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {
                        "altgraph": "*",
                        "macholib": {
                            "version": "*",
                            "markers": "sys_platform == 'darwin'",
                        },
                    },
                },
                {
                    "name": "altgraph",
                    "version": "0.17",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
                {
                    "name": "macholib",
                    "version": "1.8",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {"altgraph": ">=0.15"},
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"pyinstaller": [], "altgraph": [], "macholib": []},
            },
        }
    )
    set_package_requires(poetry, skip={"altgraph", "macholib"})

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    # Rationale for the results:
    #  * PyInstaller has an explicit dependency on altgraph, so it must always be
    #    installed.
    #  * PyInstaller requires macholib on Darwin, which in turn requires altgraph.
    # The dependency graph:
    # pyinstaller 4.0     PyInstaller bundles a Python application and all its
    # ├── altgraph *      dependencies into a single package.
    # ├── macholib >=1.8 -- only on Darwin
    # │   └── altgraph >=0.15
    python27 = 'python_version >= "2.7" and python_version < "2.8"'
    python36 = 'python_version >= "3.6" and python_version < "4.0"'
    darwin = 'sys_platform=="darwin"'
    expected = {
        "pyinstaller": Dependency.create_from_pep_508(
            f"pyinstaller==4.0 ; {python27} or {python36}"
        ),
        "altgraph": Dependency.create_from_pep_508(
            f"altgraph==0.17 ; {python27} or {python36} or {python27} and {darwin} or"
            f" {python36} and {darwin}"
        ),
        "macholib": Dependency.create_from_pep_508(
            f"macholib==1.8 ; {python27} and {darwin} or {python36} and {darwin}"
        ),
    }

    for line in content.strip().split("\n"):
        dependency = Dependency.create_from_pep_508(line)
        assert dependency.name in expected
        expected_dependency = expected.pop(dependency.name)
        assert dependency == expected_dependency
        assert dependency.marker == expected_dependency.marker


def test_exporter_can_export_requirements_txt_with_nested_packages_and_markers(
    tmp_dir: str, poetry: Poetry
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "a",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "marker": "python_version < '3.7'",
                    "dependencies": {"b": ">=0.0.0", "c": ">=0.0.0"},
                },
                {
                    "name": "b",
                    "version": "4.5.6",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "marker": "platform_system == 'Windows'",
                    "dependencies": {"d": ">=0.0.0"},
                },
                {
                    "name": "c",
                    "version": "7.8.9",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "marker": "sys_platform == 'win32'",
                    "dependencies": {"d": ">=0.0.0"},
                },
                {
                    "name": "d",
                    "version": "0.0.1",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"a": [], "b": [], "c": [], "d": []},
            },
        }
    )
    set_package_requires(poetry, skip={"b", "c", "d"})

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    python27 = 'python_version >= "2.7" and python_version < "2.8"'
    python36 = 'python_version >= "3.6" and python_version < "3.7"'
    windows = 'platform_system == "Windows"'
    win32 = 'sys_platform == "win32"'
    expected = {
        "a": Dependency.create_from_pep_508(f"a==1.2.3 ; {python27} or {python36}"),
        "b": Dependency.create_from_pep_508(
            f"b==4.5.6 ; {python27} and {windows} or {python36} and {windows}"
        ),
        "c": Dependency.create_from_pep_508(
            f"c==7.8.9 ; {python27} and {win32} or {python36} and {win32}"
        ),
        "d": Dependency.create_from_pep_508(
            f"d==0.0.1 ; {python27} and {windows} or {python36} and {windows} or"
            f" {python27} and {win32} or {python36} and {win32}"
        ),
    }

    for line in content.strip().split("\n"):
        dependency = Dependency.create_from_pep_508(line)
        assert dependency.name in expected
        expected_dependency = expected.pop(dependency.name)
        assert dependency == expected_dependency
        assert dependency.marker == expected_dependency.marker

    assert expected == {}


@pytest.mark.parametrize(
    ["dev", "lines"],
    [
        (
            False,
            [
                'a==1.2.3 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "3.8"'
            ],
        ),
        (
            True,
            [
                'a==1.2.3 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "3.8" or python_version'
                ' >= "3.6" and python_version < "4.0"',
                'b==4.5.6 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "4.0"',
            ],
        ),
    ],
)
def test_exporter_can_export_requirements_txt_with_nested_packages_and_markers_any(
    tmp_dir: str, poetry: Poetry, dev: bool, lines: list[str]
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "a",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
                {
                    "name": "b",
                    "version": "4.5.6",
                    "category": "dev",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {"a": ">=1.2.3"},
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"a": [], "b": []},
            },
        }
    )

    root = poetry.package.with_dependency_groups([], only=True)
    root.add_dependency(
        Factory.create_dependency(
            name="a", constraint={"version": "^1.2.3", "python": "<3.8"}
        )
    )
    root.add_dependency(
        Factory.create_dependency(
            name="b", constraint={"version": "^4.5.6"}, groups=["dev"]
        )
    )
    poetry._package = root

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt", dev=dev)

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    assert content.strip() == "\n".join(lines)


def test_exporter_can_export_requirements_txt_with_standard_packages_and_hashes(
    tmp_dir: str, poetry: Poetry
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": ["12345"], "bar": ["67890"]},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
bar==4.5.6 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:67890
foo==1.2.3 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:12345
"""

    assert content == expected


def test_exporter_can_export_requirements_txt_with_standard_packages_and_hashes_disabled(  # noqa: E501
    tmp_dir: str, poetry: Poetry
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": ["12345"], "bar": ["67890"]},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export(
        "requirements.txt", Path(tmp_dir), "requirements.txt", with_hashes=False
    )

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
bar==4.5.6 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
foo==1.2.3 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
"""

    assert content == expected


def test_exporter_exports_requirements_txt_without_dev_packages_by_default(
    tmp_dir: str, poetry: Poetry
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "dev",
                    "optional": False,
                    "python-versions": "*",
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": ["12345"], "bar": ["67890"]},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
foo==1.2.3 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:12345
"""

    assert content == expected


def test_exporter_exports_requirements_txt_with_dev_packages_if_opted_in(
    tmp_dir: str, poetry: Poetry
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "dev",
                    "optional": False,
                    "python-versions": "*",
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": ["12345"], "bar": ["67890"]},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt", dev=True)

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
bar==4.5.6 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:67890
foo==1.2.3 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:12345
"""

    assert content == expected


def test_exporter_exports_requirements_txt_without_optional_packages(
    tmp_dir: str, poetry: Poetry
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "dev",
                    "optional": True,
                    "python-versions": "*",
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": ["12345"], "bar": ["67890"]},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt", dev=True)

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
foo==1.2.3 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:12345
"""

    assert content == expected


@pytest.mark.parametrize(
    ["extras", "lines"],
    [
        (
            None,
            [
                'foo==1.2.3 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "4.0"'
            ],
        ),
        (
            False,
            [
                'foo==1.2.3 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "4.0"'
            ],
        ),
        (
            True,
            [
                'bar==4.5.6 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "4.0"',
                'foo==1.2.3 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "4.0"',
                'spam==0.1.0 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "4.0"',
            ],
        ),
        (
            ["feature_bar"],
            [
                'bar==4.5.6 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "4.0"',
                'foo==1.2.3 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "4.0"',
                'spam==0.1.0 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "4.0"',
            ],
        ),
    ],
)
def test_exporter_exports_requirements_txt_with_optional_packages(
    tmp_dir: str,
    poetry: Poetry,
    extras: bool | list[str] | None,
    lines: list[str],
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "main",
                    "optional": True,
                    "python-versions": "*",
                    "dependencies": {"spam": ">=0.1"},
                },
                {
                    "name": "spam",
                    "version": "0.1.0",
                    "category": "main",
                    "optional": True,
                    "python-versions": "*",
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": ["12345"], "bar": ["67890"], "spam": ["abcde"]},
            },
            "extras": {"feature_bar": ["bar"]},
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export(
        "requirements.txt",
        Path(tmp_dir),
        "requirements.txt",
        dev=True,
        with_hashes=False,
        extras=extras,
    )

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = "\n".join(lines)

    assert content.strip() == expected


def test_exporter_can_export_requirements_txt_with_git_packages(
    tmp_dir: str, poetry: Poetry
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "source": {
                        "type": "git",
                        "url": "https://github.com/foo/foo.git",
                        "reference": "123456",
                    },
                }
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": []},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
foo @ git+https://github.com/foo/foo.git@123456 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
"""

    assert content == expected


def test_exporter_can_export_requirements_txt_with_nested_packages(
    tmp_dir: str, poetry: Poetry
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "source": {
                        "type": "git",
                        "url": "https://github.com/foo/foo.git",
                        "reference": "123456",
                    },
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {"foo": "rev 123456"},
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": [], "bar": []},
            },
        }
    )
    set_package_requires(poetry, skip={"foo"})

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
bar==4.5.6 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
foo @ git+https://github.com/foo/foo.git@123456 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
"""

    assert content == expected


def test_exporter_can_export_requirements_txt_with_nested_packages_cyclic(
    tmp_dir: str, poetry: Poetry
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {"bar": {"version": "4.5.6"}},
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {"baz": {"version": "7.8.9"}},
                },
                {
                    "name": "baz",
                    "version": "7.8.9",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {"foo": {"version": "1.2.3"}},
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": [], "bar": [], "baz": []},
            },
        }
    )
    set_package_requires(poetry, skip={"bar", "baz"})

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
bar==4.5.6 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
baz==7.8.9 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
foo==1.2.3 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
"""

    assert content == expected


def test_exporter_can_export_requirements_txt_with_nested_packages_and_multiple_markers(
    tmp_dir: str, poetry: Poetry
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {
                        "bar": [
                            {
                                "version": ">=1.2.3,<7.8.10",
                                "markers": 'platform_system != "Windows"',
                            },
                            {
                                "version": ">=4.5.6,<7.8.10",
                                "markers": 'platform_system == "Windows"',
                            },
                        ]
                    },
                },
                {
                    "name": "bar",
                    "version": "7.8.9",
                    "category": "main",
                    "optional": True,
                    "python-versions": "*",
                    "dependencies": {
                        "baz": {
                            "version": "!=10.11.12",
                            "markers": 'platform_system == "Windows"',
                        }
                    },
                },
                {
                    "name": "baz",
                    "version": "10.11.13",
                    "category": "main",
                    "optional": True,
                    "python-versions": "*",
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": [], "bar": [], "baz": []},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export(
        "requirements.txt", Path(tmp_dir), "requirements.txt", with_hashes=False
    )

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
bar==7.8.9 ;\
 python_version >= "2.7" and python_version < "2.8" and platform_system != "Windows" or\
 python_version >= "3.6" and python_version < "4.0" and platform_system != "Windows" or\
 python_version >= "2.7" and python_version < "2.8" and platform_system == "Windows" or\
 python_version >= "3.6" and python_version < "4.0" and platform_system == "Windows"
baz==10.11.13 ;\
 python_version >= "2.7" and python_version < "2.8" and platform_system == "Windows" or\
 python_version >= "3.6" and python_version < "4.0" and platform_system == "Windows"
foo==1.2.3 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
"""

    assert content == expected


def test_exporter_can_export_requirements_txt_with_git_packages_and_markers(
    tmp_dir: str, poetry: Poetry
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "marker": "python_version < '3.7'",
                    "source": {
                        "type": "git",
                        "url": "https://github.com/foo/foo.git",
                        "reference": "123456",
                    },
                }
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": []},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
foo @ git+https://github.com/foo/foo.git@123456 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "3.7"
"""

    assert content == expected


def test_exporter_can_export_requirements_txt_with_directory_packages(
    tmp_dir: str, poetry: Poetry, working_directory: Path
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "source": {
                        "type": "directory",
                        "url": "tests/fixtures/sample_project",
                        "reference": "",
                    },
                }
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": []},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = f"""\
foo @ {working_directory.as_uri()}/tests/fixtures/sample_project ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
"""

    assert content == expected


def test_exporter_can_export_requirements_txt_with_nested_directory_packages(
    tmp_dir: str, poetry: Poetry, working_directory: Path
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "source": {
                        "type": "directory",
                        "url": "tests/fixtures/sample_project",
                        "reference": "",
                    },
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "source": {
                        "type": "directory",
                        "url": "tests/fixtures/sample_project/../project_with_nested_local/bar",  # noqa: E501
                        "reference": "",
                    },
                },
                {
                    "name": "baz",
                    "version": "7.8.9",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "source": {
                        "type": "directory",
                        "url": "tests/fixtures/sample_project/../project_with_nested_local/bar/..",  # noqa: E501
                        "reference": "",
                    },
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": [], "bar": [], "baz": []},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = f"""\
bar @ {working_directory.as_uri()}/tests/fixtures/project_with_nested_local/bar ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
baz @ {working_directory.as_uri()}/tests/fixtures/project_with_nested_local ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
foo @ {working_directory.as_uri()}/tests/fixtures/sample_project ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
"""

    assert content == expected


def test_exporter_can_export_requirements_txt_with_directory_packages_and_markers(
    tmp_dir: str, poetry: Poetry, working_directory: Path
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "marker": "python_version < '3.7'",
                    "source": {
                        "type": "directory",
                        "url": "tests/fixtures/sample_project",
                        "reference": "",
                    },
                }
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": []},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = f"""\
foo @ {working_directory.as_uri()}/tests/fixtures/sample_project ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "3.7"
"""

    assert content == expected


def test_exporter_can_export_requirements_txt_with_file_packages(
    tmp_dir: str, poetry: Poetry, working_directory: Path
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "source": {
                        "type": "file",
                        "url": "tests/fixtures/distributions/demo-0.1.0.tar.gz",
                        "reference": "",
                    },
                }
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": []},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = f"""\
foo @ {working_directory.as_uri()}/tests/fixtures/distributions/demo-0.1.0.tar.gz ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
"""

    assert content == expected


def test_exporter_can_export_requirements_txt_with_file_packages_and_markers(
    tmp_dir: str, poetry: Poetry, working_directory: Path
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "marker": "python_version < '3.7'",
                    "source": {
                        "type": "file",
                        "url": "tests/fixtures/distributions/demo-0.1.0.tar.gz",
                        "reference": "",
                    },
                }
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": []},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = f"""\
foo @ {working_directory.as_uri()}/tests/fixtures/distributions/demo-0.1.0.tar.gz ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "3.7"
"""

    assert content == expected


def test_exporter_exports_requirements_txt_with_legacy_packages(
    tmp_dir: str, poetry: Poetry
):
    poetry.pool.add_repository(
        LegacyRepository(
            "custom",
            "https://example.com/simple",
        )
    )
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "dev",
                    "optional": False,
                    "python-versions": "*",
                    "source": {
                        "type": "legacy",
                        "url": "https://example.com/simple",
                        "reference": "",
                    },
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": ["12345"], "bar": ["67890"]},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt", dev=True)

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
--extra-index-url https://example.com/simple

bar==4.5.6 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:67890
foo==1.2.3 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:12345
"""

    assert content == expected


def test_exporter_exports_requirements_txt_with_url_false(tmp_dir: str, poetry: Poetry):
    poetry.pool.add_repository(
        LegacyRepository(
            "custom",
            "https://example.com/simple",
        )
    )
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "dev",
                    "optional": False,
                    "python-versions": "*",
                    "source": {
                        "type": "legacy",
                        "url": "https://example.com/simple",
                        "reference": "",
                    },
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": ["12345"], "bar": ["67890"]},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export(
        "requirements.txt", Path(tmp_dir), "requirements.txt", dev=True, with_urls=False
    )

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
bar==4.5.6 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:67890
foo==1.2.3 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:12345
"""

    assert content == expected


def test_exporter_exports_requirements_txt_with_legacy_packages_trusted_host(
    tmp_dir: str, poetry: Poetry
):
    poetry.pool.add_repository(
        LegacyRepository(
            "custom",
            "http://example.com/simple",
        )
    )
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "dev",
                    "optional": False,
                    "python-versions": "*",
                    "source": {
                        "type": "legacy",
                        "url": "http://example.com/simple",
                        "reference": "",
                    },
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"bar": ["67890"]},
            },
        }
    )
    set_package_requires(poetry)
    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt", dev=True)

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
--trusted-host example.com
--extra-index-url http://example.com/simple

bar==4.5.6 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:67890
"""

    assert content == expected


@pytest.mark.parametrize(
    ["dev", "expected"],
    [
        (
            True,
            [
                'bar==1.2.2 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "4.0"',
                'baz==1.2.3 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "4.0"',
                'foo==1.2.1 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "4.0"',
            ],
        ),
        (
            False,
            [
                'bar==1.2.2 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "4.0"',
                'foo==1.2.1 ; python_version >= "2.7" and python_version < "2.8" or'
                ' python_version >= "3.6" and python_version < "4.0"',
            ],
        ),
    ],
)
def test_exporter_exports_requirements_txt_with_dev_extras(
    tmp_dir: str, poetry: Poetry, dev: bool, expected: list[str]
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.1",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
                {
                    "name": "bar",
                    "version": "1.2.2",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {
                        "baz": {
                            "version": ">=0.1.0",
                            "optional": True,
                            "markers": "extra == 'baz'",
                        }
                    },
                    "extras": {"baz": ["baz (>=0.1.0)"]},
                },
                {
                    "name": "baz",
                    "version": "1.2.3",
                    "category": "dev",
                    "optional": False,
                    "python-versions": "*",
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": [], "bar": [], "baz": []},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt", dev=dev)

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    assert content == "\n".join(expected) + "\n"


def test_exporter_exports_requirements_txt_with_legacy_packages_and_duplicate_sources(
    tmp_dir: str, poetry: Poetry
):
    poetry.pool.add_repository(
        LegacyRepository(
            "custom",
            "https://example.com/simple",
        )
    )
    poetry.pool.add_repository(
        LegacyRepository(
            "custom",
            "https://foobaz.com/simple",
        )
    )
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "source": {
                        "type": "legacy",
                        "url": "https://example.com/simple",
                        "reference": "",
                    },
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "dev",
                    "optional": False,
                    "python-versions": "*",
                    "source": {
                        "type": "legacy",
                        "url": "https://example.com/simple",
                        "reference": "",
                    },
                },
                {
                    "name": "baz",
                    "version": "7.8.9",
                    "category": "dev",
                    "optional": False,
                    "python-versions": "*",
                    "source": {
                        "type": "legacy",
                        "url": "https://foobaz.com/simple",
                        "reference": "",
                    },
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": ["12345"], "bar": ["67890"], "baz": ["24680"]},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt", dev=True)

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
--extra-index-url https://example.com/simple
--extra-index-url https://foobaz.com/simple

bar==4.5.6 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:67890
baz==7.8.9 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:24680
foo==1.2.3 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:12345
"""

    assert content == expected


def test_exporter_exports_requirements_txt_with_legacy_packages_and_credentials(
    tmp_dir: str, poetry: Poetry, config: Config
):
    poetry.config.merge(
        {
            "repositories": {"custom": {"url": "https://example.com/simple"}},
            "http-basic": {"custom": {"username": "foo", "password": "bar"}},
        }
    )
    poetry.pool.add_repository(
        LegacyRepository("custom", "https://example.com/simple", config=poetry.config)
    )
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "dev",
                    "optional": False,
                    "python-versions": "*",
                    "source": {
                        "type": "legacy",
                        "url": "https://example.com/simple",
                        "reference": "",
                    },
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": ["12345"], "bar": ["67890"]},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export(
        "requirements.txt",
        Path(tmp_dir),
        "requirements.txt",
        dev=True,
        with_credentials=True,
    )

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
--extra-index-url https://foo:bar@example.com/simple

bar==4.5.6 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:67890
foo==1.2.3 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0" \\
    --hash=sha256:12345
"""

    assert content == expected


def test_exporter_exports_requirements_txt_to_standard_output(
    tmp_dir: str, poetry: Poetry, capsys: CaptureFixture
):
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
                {
                    "name": "bar",
                    "version": "4.5.6",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                },
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": [], "bar": []},
            },
        }
    )
    set_package_requires(poetry)

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), sys.stdout)

    out, err = capsys.readouterr()
    expected = """\
bar==4.5.6 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
foo==1.2.3 ;\
 python_version >= "2.7" and python_version < "2.8" or\
 python_version >= "3.6" and python_version < "4.0"
"""

    assert out == expected


def test_exporter_doesnt_confuse_repeated_packages(
    tmp_dir: str, poetry: Poetry, capsys: CaptureFixture
):
    # Testcase derived from <https://github.com/python-poetry/poetry/issues/5141>.
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "celery",
                    "version": "5.1.2",
                    "category": "main",
                    "optional": False,
                    "python-versions": "<3.7",
                    "dependencies": {
                        "click": ">=7.0,<8.0",
                        "click-didyoumean": ">=0.0.3",
                        "click-plugins": ">=1.1.1",
                    },
                },
                {
                    "name": "celery",
                    "version": "5.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": ">=3.7",
                    "dependencies": {
                        "click": ">=8.0.3,<9.0",
                        "click-didyoumean": ">=0.0.3",
                        "click-plugins": ">=1.1.1",
                    },
                },
                {
                    "name": "click",
                    "version": "7.1.2",
                    "category": "main",
                    "optional": False,
                    "python-versions": (
                        ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*"
                    ),
                },
                {
                    "name": "click",
                    "version": "8.0.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": ">=3.6",
                    "dependencies": {},
                },
                {
                    "name": "click-didyoumean",
                    "version": "0.0.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {"click": "*"},
                },
                {
                    "name": "click-didyoumean",
                    "version": "0.3.0",
                    "category": "main",
                    "optional": False,
                    "python-versions": ">=3.6.2,<4.0.0",
                    "dependencies": {"click": ">=7"},
                },
                {
                    "name": "click-plugins",
                    "version": "1.1.1",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "dependencies": {"click": ">=4.0"},
                },
            ],
            "metadata": {
                "lock-version": "1.1",
                "python-versions": "^3.6",
                "content-hash": (
                    "832b13a88e5020c27cbcd95faa577bf0dbf054a65c023b45dc9442b640d414e6"
                ),
                "hashes": {
                    "celery": [],
                    "click-didyoumean": [],
                    "click-plugins": [],
                    "click": [],
                },
            },
        }
    )
    root = poetry.package.with_dependency_groups([], only=True)
    root.python_versions = "^3.6"
    root.add_dependency(
        Factory.create_dependency(
            name="celery", constraint={"version": "5.1.2", "python": "<3.7"}
        )
    )
    root.add_dependency(
        Factory.create_dependency(
            name="celery", constraint={"version": "5.2.3", "python": ">=3.7"}
        )
    )
    poetry._package = root

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), sys.stdout)

    out, err = capsys.readouterr()
    expected = """\
celery==5.1.2 ; python_version >= "3.6" and python_version < "3.7"
celery==5.2.3 ; python_version >= "3.7" and python_version < "4.0"
click-didyoumean==0.0.3 ; python_version >= "3.6" and python_version < "3.7"
click-didyoumean==0.3.0 ; python_version >= "3.7" and python_full_version < "4.0.0"
click-plugins==1.1.1 ;\
 python_version >= "3.6" and python_version < "3.7" or\
 python_version >= "3.7" and python_version < "4.0"
click==7.1.2 ; python_version >= "3.6" and python_version < "3.7"
click==8.0.3 ;\
 python_version >= "3.7" and python_version < "4.0" or\
 python_version >= "3.7" and python_full_version < "4.0.0"
"""

    assert out == expected


def test_exporter_handles_extras_next_to_non_extras(
    tmp_dir: str, poetry: Poetry, capsys: CaptureFixture
):
    # Testcase similar to the solver testcase added at #5305.
    poetry.locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "localstack",
                    "python-versions": "*",
                    "version": "1.0.0",
                    "category": "main",
                    "optional": False,
                    "dependencies": {
                        "localstack-ext": [
                            {"version": ">=1.0.0"},
                            {
                                "version": ">=1.0.0",
                                "extras": ["bar"],
                                "markers": 'extra == "foo"',
                            },
                        ]
                    },
                    "extras": {"foo": ["localstack-ext (>=1.0.0)"]},
                },
                {
                    "name": "localstack-ext",
                    "python-versions": "*",
                    "version": "1.0.0",
                    "category": "main",
                    "optional": False,
                    "dependencies": {
                        "something": "*",
                        "something-else": {
                            "version": ">=1.0.0",
                            "markers": 'extra == "bar"',
                        },
                        "another-thing": {
                            "version": ">=1.0.0",
                            "markers": 'extra == "baz"',
                        },
                    },
                    "extras": {
                        "bar": ["something-else (>=1.0.0)"],
                        "baz": ["another-thing (>=1.0.0)"],
                    },
                },
                {
                    "name": "something",
                    "python-versions": "*",
                    "version": "1.0.0",
                    "category": "main",
                    "optional": False,
                    "dependencies": {},
                },
                {
                    "name": "something-else",
                    "python-versions": "*",
                    "version": "1.0.0",
                    "category": "main",
                    "optional": False,
                    "dependencies": {},
                },
                {
                    "name": "another-thing",
                    "python-versions": "*",
                    "version": "1.0.0",
                    "category": "main",
                    "optional": False,
                    "dependencies": {},
                },
            ],
            "metadata": {
                "lock-version": "1.1",
                "python-versions": "^3.6",
                "content-hash": (
                    "832b13a88e5020c27cbcd95faa577bf0dbf054a65c023b45dc9442b640d414e6"
                ),
                "hashes": {
                    "localstack": [],
                    "localstack-ext": [],
                    "something": [],
                    "something-else": [],
                    "another-thing": [],
                },
            },
        }
    )
    root = poetry.package.with_dependency_groups([], only=True)
    root.python_versions = "^3.6"
    root.add_dependency(
        Factory.create_dependency(
            name="localstack", constraint={"version": "^1.0.0", "extras": ["foo"]}
        )
    )
    poetry._package = root

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), sys.stdout)

    out, err = capsys.readouterr()
    expected = """\
localstack-ext==1.0.0 ; python_version >= "3.6" and python_version < "4.0"
localstack==1.0.0 ; python_version >= "3.6" and python_version < "4.0"
something-else==1.0.0 ; python_version >= "3.6" and python_version < "4.0"
something==1.0.0 ; python_version >= "3.6" and python_version < "4.0"
"""

    assert out == expected
