import os
import shutil
import urllib.parse

from pathlib import Path

from poetry.console.application import Application
from poetry.core.masonry.utils.helpers import escape_name
from poetry.core.masonry.utils.helpers import escape_version
from poetry.core.packages.package import Package
from poetry.core.packages.utils.link import Link
from poetry.core.toml.file import TOMLFile
from poetry.core.vcs.git import ParsedUrl
from poetry.factory import Factory
from poetry.installation.executor import Executor
from poetry.packages import Locker
from poetry.repositories import Repository
from poetry.repositories.exceptions import PackageNotFound
from poetry.utils._compat import WINDOWS


FIXTURE_PATH = Path(__file__).parent / "fixtures"


def get_package(name, version):
    return Package(name, version)


def get_dependency(
    name, constraint=None, groups=None, optional=False, allows_prereleases=False
):
    if constraint is None:
        constraint = "*"

    if isinstance(constraint, str):
        constraint = {"version": constraint}

    constraint["optional"] = optional
    constraint["allow_prereleases"] = allows_prereleases

    return Factory.create_dependency(name, constraint or "*", groups=groups)


def fixture(path=None):
    if path:
        return FIXTURE_PATH / path
    else:
        return FIXTURE_PATH


def copy_or_symlink(source, dest):
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


def mock_clone(_, source, dest):
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


def mock_download(url, dest, **__):
    parts = urllib.parse.urlparse(url)

    fixtures = Path(__file__).parent / "fixtures"
    fixture = fixtures / parts.path.lstrip("/")

    copy_or_symlink(fixture, Path(dest))


class TestExecutor(Executor):
    def __init__(self, *args, **kwargs):
        super(TestExecutor, self).__init__(*args, **kwargs)

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
        super(TestExecutor, self)._do_execute_operation(operation)

        if not operation.skipped:
            getattr(self, "_{}s".format(operation.job_type)).append(operation.package)

    def _execute_install(self, operation):
        return 0

    def _execute_update(self, operation):
        return 0

    def _execute_remove(self, operation):
        return 0


class TestApplication(Application):
    def __init__(self, poetry):
        super(TestApplication, self).__init__()
        self._poetry = poetry

    def reset_poetry(self):
        poetry = self._poetry
        self._poetry = Factory().create_poetry(self._poetry.file.path.parent)
        self._poetry.set_pool(poetry.pool)
        self._poetry.set_config(poetry.config)
        self._poetry.set_locker(
            TestLocker(poetry.locker.lock.path, self._poetry.local_config)
        )


class TestLocker(Locker):
    def __init__(self, lock, local_config):  # noqa
        self._lock = TOMLFile(lock)
        self._local_config = local_config
        self._lock_data = None
        self._content_hash = self._get_content_hash()
        self._locked = False
        self._lock_data = None
        self._write = False

    def write(self, write=True):
        self._write = write

    def is_locked(self):
        return self._locked

    def locked(self, is_locked=True):
        self._locked = is_locked

        return self

    def mock_lock_data(self, data):
        self.locked()

        self._lock_data = data

    def is_fresh(self):
        return True

    def _write_lock_data(self, data):
        if self._write:
            super(TestLocker, self)._write_lock_data(data)
            self._locked = True
            return

        self._lock_data = data


class TestRepository(Repository):
    def find_packages(self, dependency):
        packages = super(TestRepository, self).find_packages(dependency)
        if len(packages) == 0:
            raise PackageNotFound("Package [{}] not found.".format(dependency.name))

        return packages

    def find_links_for_package(self, package):
        return [
            Link(
                "https://foo.bar/files/{}-{}-py2.py3-none-any.whl".format(
                    escape_name(package.name), escape_version(package.version.text)
                )
            )
        ]
