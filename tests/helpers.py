import os
import shutil

from poetry.packages import Dependency
from poetry.packages import Package
from poetry.utils._compat import PY2
from poetry.utils._compat import WINDOWS
from poetry.utils._compat import Path
from poetry.utils._compat import urlparse
from poetry.vcs.git import ParsedUrl


FIXTURE_PATH = Path(__file__).parent / "fixtures"


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


def mock_download(self, url, dest):
    parts = urlparse.urlparse(url)

    fixtures = Path(__file__).parent / "fixtures"
    fixture = fixtures / parts.path.lstrip("/")

    copy_or_symlink(fixture, dest)
