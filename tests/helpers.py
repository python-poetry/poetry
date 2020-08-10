import os
import shutil

from typing import Any
from typing import Dict

from poetry.config.config import Config as BaseConfig
from poetry.core.packages import Dependency
from poetry.core.packages import Package
from poetry.core.vcs.git import ParsedUrl
from poetry.installation.executor import Executor as BaseExecutor
from poetry.utils._compat import PY2
from poetry.utils._compat import WINDOWS
from poetry.utils._compat import Path
from poetry.utils._compat import urlparse


FIXTURE_PATH = Path(__file__).parent / "fixtures"


class Config(BaseConfig):
    def get(self, setting_name, default=None):  # type: (str, Any) -> Any
        self.merge(self._config_source.config)
        self.merge(self._auth_config_source.config)

        return super(Config, self).get(setting_name, default=default)

    def raw(self):  # type: () -> Dict[str, Any]
        self.merge(self._config_source.config)
        self.merge(self._auth_config_source.config)

        return super(Config, self).raw()

    def all(self):  # type: () -> Dict[str, Any]
        self.merge(self._config_source.config)
        self.merge(self._auth_config_source.config)

        return super(Config, self).all()


def get_package(name, version):
    return Package(name, version)


def get_dependency(
    name, constraint=None, category="main", optional=False, allows_prereleases=False
):
    return Dependency(
        name,
        constraint or "*",
        category=category,
        optional=optional,
        allows_prereleases=allows_prereleases,
    )


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
        if PY2:
            if source.is_dir():
                shutil.copytree(str(source), str(dest))
            else:
                shutil.copyfile(str(source), str(dest))
        else:
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
    parts = urlparse.urlparse(url)

    fixtures = Path(__file__).parent / "fixtures"
    fixture = fixtures / parts.path.lstrip("/")

    copy_or_symlink(fixture, Path(dest))


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

    def _execute_remove(self, operation):
        return 0
