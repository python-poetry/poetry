import sys

from pathlib import Path

import pytest

from poetry.core.packages.dependency import Dependency
from poetry.core.toml.file import TOMLFile
from poetry.factory import Factory
from poetry.packages import Locker as BaseLocker
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.utils.exporter import Exporter


class Locker(BaseLocker):
    def __init__(self):
        self._lock = TOMLFile(Path.cwd().joinpath("poetry.lock"))
        self._locked = True
        self._content_hash = self._get_content_hash()

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


@pytest.fixture
def working_directory():
    return Path(__file__).parent.parent.parent


@pytest.fixture(autouse=True)
def mock_path_cwd(mocker, working_directory):
    yield mocker.patch("pathlib.Path.cwd", return_value=working_directory)


@pytest.fixture()
def locker():
    return Locker()


@pytest.fixture
def poetry(fixture_dir, locker):
    p = Factory().create_poetry(fixture_dir("sample_project"))
    p._locker = locker

    return p


def set_package_requires(poetry, skip=None):
    skip = skip or set()
    packages = poetry.locker.locked_repository(with_dev_reqs=True).packages
    package = poetry.package.with_dependency_groups([], only=True)
    for pkg in packages:
        if pkg.name not in skip:
            package.add_dependency(pkg.to_dependency())

    poetry._package = package


def test_exporter_can_export_requirements_txt_with_standard_packages(
    tmp_dir, poetry, mocker
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
bar==4.5.6
foo==1.2.3
"""

    assert expected == content


def test_exporter_can_export_requirements_txt_with_standard_packages_and_markers(
    tmp_dir, poetry
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
bar==4.5.6
baz==7.8.9; sys_platform == "win32"
foo==1.2.3; python_version < "3.7"
"""

    assert expected == content


def test_exporter_can_export_requirements_txt_poetry(tmp_dir, poetry):
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
    # junit-xml 1.9 Creates JUnit XML test result documents that can be read by tools such as Jenkins
    # └── six *
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
    expected = {
        "poetry": Dependency.create_from_pep_508("poetry==1.1.4"),
        "junit-xml": Dependency.create_from_pep_508("junit-xml==1.9"),
        "keyring": Dependency.create_from_pep_508("keyring==21.8.0"),
        "secretstorage": Dependency.create_from_pep_508(
            "secretstorage==3.3.0; sys_platform=='linux'"
        ),
        "cryptography": Dependency.create_from_pep_508(
            "cryptography==3.2; sys_platform=='linux'"
        ),
        "six": Dependency.create_from_pep_508("six==1.15.0"),
    }

    for line in content.strip().split("\n"):
        dependency = Dependency.create_from_pep_508(line)
        assert dependency.name in expected
        expected_dependency = expected.pop(dependency.name)
        assert dependency == expected_dependency
        assert dependency.marker == expected_dependency.marker


def test_exporter_can_export_requirements_txt_pyinstaller(tmp_dir, poetry):
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
    #  * PyInstaller has an explicit dependency on altgraph, so it must always be installed.
    #  * PyInstaller requires macholib on Darwin, which in turn requires altgraph.
    # The dependency graph:
    # pyinstaller 4.0 PyInstaller bundles a Python application and all its dependencies into a single package.
    # ├── altgraph *
    # ├── macholib >=1.8 -- only on Darwin
    # │   └── altgraph >=0.15
    expected = {
        "pyinstaller": Dependency.create_from_pep_508("pyinstaller==4.0"),
        "altgraph": Dependency.create_from_pep_508("altgraph==0.17"),
        "macholib": Dependency.create_from_pep_508(
            "macholib==1.8; sys_platform == 'darwin'"
        ),
    }

    for line in content.strip().split("\n"):
        dependency = Dependency.create_from_pep_508(line)
        assert dependency.name in expected
        expected_dependency = expected.pop(dependency.name)
        assert dependency == expected_dependency
        assert dependency.marker == expected_dependency.marker


def test_exporter_can_export_requirements_txt_with_nested_packages_and_markers(
    tmp_dir, poetry
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

    expected = {
        "a": Dependency.create_from_pep_508("a==1.2.3; python_version < '3.7'"),
        "b": Dependency.create_from_pep_508(
            "b==4.5.6; platform_system == 'Windows' and python_version < '3.7'"
        ),
        "c": Dependency.create_from_pep_508(
            "c==7.8.9; sys_platform == 'win32' and python_version < '3.7'"
        ),
        "d": Dependency.create_from_pep_508(
            "d==0.0.1; platform_system == 'Windows' and python_version < '3.7' or sys_platform == 'win32' and python_version < '3.7'"
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
    "dev,lines",
    [(False, ['a==1.2.3; python_version < "3.8"']), (True, ["a==1.2.3", "b==4.5.6"])],
)
def test_exporter_can_export_requirements_txt_with_nested_packages_and_markers_any(
    tmp_dir, poetry, dev, lines
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
            name="a", constraint=dict(version="^1.2.3", python="<3.8")
        )
    )
    root.add_dependency(
        Factory.create_dependency(
            name="b", constraint=dict(version="^4.5.6"), groups=["dev"]
        )
    )
    poetry._package = root

    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt", dev=dev)

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    assert content.strip() == "\n".join(lines)


def test_exporter_can_export_requirements_txt_with_standard_packages_and_hashes(
    tmp_dir, poetry
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
bar==4.5.6 \\
    --hash=sha256:67890
foo==1.2.3 \\
    --hash=sha256:12345
"""

    assert expected == content


def test_exporter_can_export_requirements_txt_with_standard_packages_and_hashes_disabled(
    tmp_dir, poetry
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
bar==4.5.6
foo==1.2.3
"""

    assert expected == content


def test_exporter_exports_requirements_txt_without_dev_packages_by_default(
    tmp_dir, poetry
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
foo==1.2.3 \\
    --hash=sha256:12345
"""

    assert expected == content


def test_exporter_exports_requirements_txt_with_dev_packages_if_opted_in(
    tmp_dir, poetry
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
bar==4.5.6 \\
    --hash=sha256:67890
foo==1.2.3 \\
    --hash=sha256:12345
"""

    assert expected == content


def test_exporter_exports_requirements_txt_without_optional_packages(tmp_dir, poetry):
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
foo==1.2.3 \\
    --hash=sha256:12345
"""

    assert expected == content


@pytest.mark.parametrize(
    "extras,lines",
    [
        (None, ["foo==1.2.3"]),
        (False, ["foo==1.2.3"]),
        (True, ["bar==4.5.6", "foo==1.2.3", "spam==0.1.0"]),
        (["feature_bar"], ["bar==4.5.6", "foo==1.2.3", "spam==0.1.0"]),
    ],
)
def test_exporter_exports_requirements_txt_with_optional_packages(
    tmp_dir, poetry, extras, lines
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


def test_exporter_can_export_requirements_txt_with_git_packages(tmp_dir, poetry):
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
foo @ git+https://github.com/foo/foo.git@123456
"""

    assert expected == content


def test_exporter_can_export_requirements_txt_with_nested_packages(tmp_dir, poetry):
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
bar==4.5.6
foo @ git+https://github.com/foo/foo.git@123456
"""

    assert expected == content


def test_exporter_can_export_requirements_txt_with_nested_packages_cyclic(
    tmp_dir, poetry
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
bar==4.5.6
baz==7.8.9
foo==1.2.3
"""

    assert expected == content


def test_exporter_can_export_requirements_txt_with_git_packages_and_markers(
    tmp_dir, poetry
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
foo @ git+https://github.com/foo/foo.git@123456 ; python_version < "3.7"
"""

    assert expected == content


def test_exporter_can_export_requirements_txt_with_directory_packages(
    tmp_dir, poetry, working_directory
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

    expected = """\
foo @ {}/tests/fixtures/sample_project
""".format(
        working_directory.as_uri()
    )

    assert expected == content


def test_exporter_can_export_requirements_txt_with_nested_directory_packages(
    tmp_dir, poetry, working_directory
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
                        "url": "tests/fixtures/sample_project/../project_with_nested_local/bar",
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
                        "url": "tests/fixtures/sample_project/../project_with_nested_local/bar/..",
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

    expected = """\
bar @ {}/tests/fixtures/project_with_nested_local/bar
baz @ {}/tests/fixtures/project_with_nested_local
foo @ {}/tests/fixtures/sample_project
""".format(
        working_directory.as_uri(),
        working_directory.as_uri(),
        working_directory.as_uri(),
    )

    assert expected == content


def test_exporter_can_export_requirements_txt_with_directory_packages_and_markers(
    tmp_dir, poetry, working_directory
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

    expected = """\
foo @ {}/tests/fixtures/sample_project; python_version < "3.7"
""".format(
        working_directory.as_uri()
    )

    assert expected == content


def test_exporter_can_export_requirements_txt_with_file_packages(
    tmp_dir, poetry, working_directory
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

    expected = """\
foo @ {}/tests/fixtures/distributions/demo-0.1.0.tar.gz
""".format(
        working_directory.as_uri()
    )

    assert expected == content


def test_exporter_can_export_requirements_txt_with_file_packages_and_markers(
    tmp_dir, poetry, working_directory
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

    expected = """\
foo @ {}/tests/fixtures/distributions/demo-0.1.0.tar.gz; python_version < "3.7"
""".format(
        working_directory.as_uri()
    )

    assert expected == content


def test_exporter_exports_requirements_txt_with_legacy_packages(tmp_dir, poetry):
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

bar==4.5.6 \\
    --hash=sha256:67890
foo==1.2.3 \\
    --hash=sha256:12345
"""

    assert expected == content


def test_exporter_exports_requirements_txt_with_legacy_packages_trusted_host(
    tmp_dir, poetry
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

bar==4.5.6 \\
    --hash=sha256:67890
"""

    assert expected == content


@pytest.mark.parametrize(
    ("dev", "expected"),
    [
        (True, ["bar==1.2.2", "baz==1.2.3", "foo==1.2.1"]),
        (False, ["bar==1.2.2", "foo==1.2.1"]),
    ],
)
def test_exporter_exports_requirements_txt_with_dev_extras(
    tmp_dir, poetry, dev, expected
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

    assert content == "{}\n".format("\n".join(expected))


def test_exporter_exports_requirements_txt_with_legacy_packages_and_duplicate_sources(
    tmp_dir, poetry
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

bar==4.5.6 \\
    --hash=sha256:67890
baz==7.8.9 \\
    --hash=sha256:24680
foo==1.2.3 \\
    --hash=sha256:12345
"""

    assert expected == content


def test_exporter_exports_requirements_txt_with_legacy_packages_and_credentials(
    tmp_dir, poetry, config
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

bar==4.5.6 \\
    --hash=sha256:67890
foo==1.2.3 \\
    --hash=sha256:12345
"""

    assert expected == content


def test_exporter_exports_requirements_txt_to_standard_output(tmp_dir, poetry, capsys):
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
bar==4.5.6
foo==1.2.3
"""

    assert out == expected
