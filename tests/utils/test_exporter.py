import pytest

from poetry.packages import Locker as BaseLocker
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


def test_exporter_can_export_requirements_txt_with_standard_packages(tmp_dir, locker):
    locker.mock_lock_data(
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
    exporter = Exporter(locker)

    exporter.export("requirements.txt", Path(tmp_dir))

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
bar==4.5.6
foo==1.2.3
"""

    assert expected == content


def test_exporter_can_export_requirements_txt_with_standard_packages_and_hashes(
    tmp_dir, locker
):
    locker.mock_lock_data(
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
    exporter = Exporter(locker)

    exporter.export("requirements.txt", Path(tmp_dir))

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
    tmp_dir, locker
):
    locker.mock_lock_data(
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
    exporter = Exporter(locker)

    exporter.export("requirements.txt", Path(tmp_dir), with_hashes=False)

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
bar==4.5.6
foo==1.2.3
"""

    assert expected == content


def test_exporter_exports_requirements_txt_without_dev_packages_by_default(
    tmp_dir, locker
):
    locker.mock_lock_data(
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
    exporter = Exporter(locker)

    exporter.export("requirements.txt", Path(tmp_dir))

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
foo==1.2.3 \\
    --hash=sha256:12345
"""

    assert expected == content


def test_exporter_exports_requirements_txt_with_dev_packages_if_opted_in(
    tmp_dir, locker
):
    locker.mock_lock_data(
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
    exporter = Exporter(locker)

    exporter.export("requirements.txt", Path(tmp_dir), dev=True)

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
bar==4.5.6 \\
    --hash=sha256:67890
foo==1.2.3 \\
    --hash=sha256:12345
"""

    assert expected == content


def test_exporter_can_export_requirements_txt_with_git_packages(tmp_dir, locker):
    locker.mock_lock_data(
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
    exporter = Exporter(locker)

    exporter.export("requirements.txt", Path(tmp_dir))

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
-e git+https://github.com/foo/foo.git@123456#egg=foo
"""

    assert expected == content


def test_exporter_can_export_requirements_txt_with_directory_packages(tmp_dir, locker):
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "source": {"type": "directory", "url": "../foo", "reference": ""},
                }
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": []},
            },
        }
    )
    exporter = Exporter(locker)

    exporter.export("requirements.txt", Path(tmp_dir))

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
-e ../foo
"""

    assert expected == content


def test_exporter_can_export_requirements_txt_with_file_packages(tmp_dir, locker):
    locker.mock_lock_data(
        {
            "package": [
                {
                    "name": "foo",
                    "version": "1.2.3",
                    "category": "main",
                    "optional": False,
                    "python-versions": "*",
                    "source": {"type": "file", "url": "../foo.tar.gz", "reference": ""},
                }
            ],
            "metadata": {
                "python-versions": "*",
                "content-hash": "123456789",
                "hashes": {"foo": []},
            },
        }
    )
    exporter = Exporter(locker)

    exporter.export("requirements.txt", Path(tmp_dir))

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
-e ../foo.tar.gz
"""

    assert expected == content


def test_exporter_exports_requirements_txt_with_legacy_packages(tmp_dir, locker):
    locker.mock_lock_data(
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
                        "url": "https://example.com/simple/",
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
    exporter = Exporter(locker)

    exporter.export("requirements.txt", Path(tmp_dir), dev=True)

    with (Path(tmp_dir) / "requirements.txt").open(encoding="utf-8") as f:
        content = f.read()

    expected = """\
bar==4.5.6 \\
    --index-url https://example.com/simple/ \\
    --hash=sha256:67890
foo==1.2.3 \\
    --hash=sha256:12345
"""

    assert expected == content
