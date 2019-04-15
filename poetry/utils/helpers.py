import os
import re
import shutil
import stat
import tempfile
import time

from contextlib import contextmanager
from typing import List
from typing import Optional
from typing import Union

from poetry.config import Config
from poetry.version import Version

_canonicalize_regex = re.compile("[-_]+")


def canonicalize_name(name):  # type: (str) -> str
    return _canonicalize_regex.sub("-", name).lower()


def module_name(name):  # type: (str) -> str
    return canonicalize_name(name).replace(".", "_").replace("-", "_")


def normalize_version(version):  # type: (str) -> str
    return str(Version(version))


@contextmanager
def temporary_directory(*args, **kwargs):
    name = tempfile.mkdtemp(*args, **kwargs)

    yield name

    robust_rmtree(name)


def robust_rmtree(path, max_retries=3):
    """Robustly tries to delete paths.

    Retries several times if an OSError occurs.
    If the final attempt fails, the Exception is propagated
    to the caller.
    """
    for i in range(max_retries - 1):
        try:
            shutil.rmtree(path)
            return  # Only hits this on success
        except OSError:
            time.sleep(2)

    # Final attempt, pass any Exceptions up to caller.
    shutil.rmtree(path)


def parse_requires(requires):  # type: (str) -> List[str]
    lines = requires.split("\n")

    requires_dist = []
    in_section = False
    current_marker = None
    for line in lines:
        line = line.strip()
        if not line:
            if in_section:
                in_section = False

            continue

        if line.startswith("["):
            # extras or conditional dependencies
            marker = line.lstrip("[").rstrip("]")
            if ":" not in marker:
                extra, marker = marker, None
            else:
                extra, marker = marker.split(":")

            if extra:
                if marker:
                    marker = '{} and extra == "{}"'.format(marker, extra)
                else:
                    marker = 'extra == "{}"'.format(extra)

            if marker:
                current_marker = marker

            continue

        if current_marker:
            line = "{}; {}".format(line, current_marker)

        requires_dist.append(line)

    return requires_dist


def get_http_basic_auth(
    config, repository_name
):  # type: (Config, str) -> Optional[tuple]
    repo_auth = config.setting("http-basic.{}".format(repository_name))
    if repo_auth:
        return repo_auth["username"], repo_auth.get("password")

    return None


def _on_rm_error(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def safe_rmtree(path):
    shutil.rmtree(path, onerror=_on_rm_error)
