import sys

import pytest

from poetry.factory import Factory
from poetry.packages import Locker as BaseLocker
from poetry.repositories.auth import Auth
from poetry.repositories.legacy_repository import LegacyRepository
from poetry.utils._compat import Path
from poetry.utils.exporter import Exporter


class Locker(BaseLocker):
    def __init__(self):
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


@pytest.fixture()
def locker():
    return Locker()


@pytest.fixture
def poetry(fixture_dir, locker):
    p = Factory().create_poetry(fixture_dir("sample_project"))
    p._locker = locker

    return p


def test_exporter_can_export_requirements_txt_with_standard_packages(tmp_dir, poetry):
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
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": [], "bar": []},
            },
        }
    )
    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
bar==4.5.6; extra == "foo"
foo==1.2.3; python_version < "3.7"
"""

    assert expected == content


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
    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt", dev=True)

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
foo==1.2.3 \\
    --hash=sha256:12345
"""

    assert expected == content


def test_exporter_exports_requirements_txt_with_optional_packages_if_opted_in(
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
    exporter = Exporter(poetry)

    exporter.export(
        "requirements.txt",
        Path(tmp_dir),
        "requirements.txt",
        dev=True,
        extras=["feature_bar"],
    )

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
bar==4.5.6 \\
    --hash=sha256:67890
foo==1.2.3 \\
    --hash=sha256:12345
spam==0.1.0 \\
    --hash=sha256:abcde
"""

    assert expected == content


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
    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
-e git+https://github.com/foo/foo.git@123456#egg=foo
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
    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
-e git+https://github.com/foo/foo.git@123456#egg=foo; python_version < "3.7"
"""

    assert expected == content


def test_exporter_can_export_requirements_txt_with_directory_packages(tmp_dir, poetry):
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
    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
-e tests/fixtures/sample_project
"""

    assert expected == content


def test_exporter_can_export_requirements_txt_with_directory_packages_and_markers(
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
    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
-e tests/fixtures/sample_project; python_version < "3.7"
"""

    assert expected == content


def test_exporter_can_export_requirements_txt_with_file_packages(tmp_dir, poetry):
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
    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
tests/fixtures/distributions/demo-0.1.0.tar.gz
"""

    assert expected == content


def test_exporter_can_export_requirements_txt_with_file_packages_and_markers(
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
    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), "requirements.txt")

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
tests/fixtures/distributions/demo-0.1.0.tar.gz; python_version < "3.7"
"""

    assert expected == content


def test_exporter_exports_requirements_txt_with_legacy_packages(tmp_dir, poetry):
    poetry.pool.add_repository(
        LegacyRepository(
            "custom",
            "https://example.com/simple",
            auth=Auth("https://example.com/simple", "foo", "bar"),
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


def test_exporter_exports_requirements_txt_with_legacy_packages_and_duplicate_sources(
    tmp_dir, poetry
):
    poetry.pool.add_repository(
        LegacyRepository(
            "custom",
            "https://example.com/simple",
            auth=Auth("https://example.com/simple", "foo", "bar"),
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
    poetry.pool.add_repository(
        LegacyRepository(
            "custom",
            "https://example.com/simple",
            auth=Auth("https://example.com/simple", "foo", "bar"),
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
    exporter = Exporter(poetry)

    exporter.export("requirements.txt", Path(tmp_dir), sys.stdout)

    out, err = capsys.readouterr()
    expected = """\
bar==4.5.6
foo==1.2.3
"""

    assert out == expected
