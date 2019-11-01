import os
import re
import shutil
import stat
import tempfile

from contextlib import contextmanager
from typing import List
from typing import Optional

from keyring import delete_password
from keyring import get_password
from keyring import set_password
from keyring.errors import KeyringError

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


@contextmanager
def temporary_directory(*args, **kwargs):
    try:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory(*args, **kwargs) as name:
            yield name
    except ImportError:
        name = tempfile.mkdtemp(*args, **kwargs)

        yield name

        shutil.rmtree(name)


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


def keyring_service_name(repository_name):  # type: (str) -> str
    return "{}-{}".format("poetry-repository", repository_name)


def keyring_repository_password_get(
    repository_name, username
):  # type: (str, str) -> Optional[str]
    try:
        return get_password(keyring_service_name(repository_name), username)
    except (RuntimeError, KeyringError):
        return None


def keyring_repository_password_set(
    repository_name, username, password
):  # type: (str, str, str) -> None
    try:
        set_password(keyring_service_name(repository_name), username, password)
    except (RuntimeError, KeyringError):
        raise RuntimeError("Failed to store password in keyring")


def keyring_repository_password_del(
    config, repository_name
):  # type: (Config, str) -> None
    try:
        repo_auth = config.get("http-basic.{}".format(repository_name))
        if repo_auth and "username" in repo_auth:
            delete_password(
                keyring_service_name(repository_name), repo_auth["username"]
            )
    except (RuntimeError, KeyringError):
        pass


def get_http_basic_auth(
    config, repository_name
):  # type: (Config, str) -> Optional[tuple]
    repo_auth = config.get("http-basic.{}".format(repository_name))
    if repo_auth:
        username, password = repo_auth["username"], repo_auth.get("password")
        if password is None:
            password = keyring_repository_password_get(repository_name, username)
        return username, password
    return None


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
    os.chmod(path, stat.S_IWRITE)
    func(path)


def safe_rmtree(path):
    shutil.rmtree(path, onerror=_on_rm_error)


def merge_dicts(d1, d2):
    for k, v in d2.items():
        if k in d1 and isinstance(d1[k], dict) and isinstance(d2[k], Mapping):
            merge_dicts(d1[k], d2[k])
        else:
            d1[k] = d2[k]
