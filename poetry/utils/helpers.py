import os
import re
import shutil
import stat
import tempfile

from contextlib import contextmanager
from typing import List
from typing import Optional

from poetry.config.config import Config
from poetry.utils._compat import Path
from poetry.version import Version


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
            line = "{} ; {}".format(line, current_marker)

        requires_dist.append(line)

    return requires_dist


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
