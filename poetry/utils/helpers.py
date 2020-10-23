import os
import re
import shutil
import stat
import tempfile

from contextlib import contextmanager
from typing import List
from typing import Optional

import requests

from poetry.config.config import Config
from poetry.core.packages.package import Package
from poetry.core.version import Version
from poetry.utils._compat import Path


try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping


_canonicalize_regex = re.compile("[-_]+")


def canonicalize_name(name):  # type: (str) -> str
    return _canonicalize_regex.sub("-", name).lower()


def module_name(name):  # type: (str) -> str
    return canonicalize_name(name).replace(".", "_").replace("-", "_")


def normalize_version(version):  # type: (str) -> str
    return str(Version(version))


def _del_ro(action, name, exc):
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


@contextmanager
def temporary_directory(*args, **kwargs):
    name = tempfile.mkdtemp(*args, **kwargs)

    yield name

    shutil.rmtree(name, onerror=_del_ro)


def get_cert(config, repository_name):  # type: (Config, str) -> Optional[Path]
    cert = config.get("certificates.{}.cert".format(repository_name))
    if cert:
        return Path(cert)
    else:
        return None


def get_client_cert(config, repository_name):  # type: (Config, str) -> Optional[Path]
    client_cert = config.get("certificates.{}.client-cert".format(repository_name))
    if client_cert:
        return Path(client_cert)
    else:
        return None


def _on_rm_error(func, path, exc_info):
    if not os.path.exists(path):
        return

    os.chmod(path, stat.S_IWRITE)
    func(path)


def safe_rmtree(path):
    if Path(path).is_symlink():
        return os.unlink(str(path))

    shutil.rmtree(path, onerror=_on_rm_error)


def merge_dicts(d1, d2):
    for k, v in d2.items():
        if k in d1 and isinstance(d1[k], dict) and isinstance(d2[k], Mapping):
            merge_dicts(d1[k], d2[k])
        else:
            d1[k] = d2[k]


def download_file(
    url, dest, session=None, chunk_size=1024
):  # type: (str, str, Optional[requests.Session], int) -> None
    get = requests.get if not session else session.get

    with get(url, stream=True) as response:
        response.raise_for_status()

        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)


def get_package_version_display_string(
    package, root=None
):  # type: (Package, Optional[Path]) -> str
    if package.source_type in ["file", "directory"] and root:
        return "{} {}".format(
            package.version,
            Path(os.path.relpath(package.source_url, root.as_posix())).as_posix(),
        )

    return package.full_pretty_version


def paths_csv(paths):  # type: (List[Path]) -> str
    return ", ".join('"{}"'.format(str(c)) for c in paths)


def is_dir_writable(path, create=False):  # type: (Path, bool) -> bool
    try:
        if not path.exists():
            if not create:
                return False
            path.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryFile(dir=str(path)):
            pass
    except (IOError, OSError):
        return False
    else:
        return True
