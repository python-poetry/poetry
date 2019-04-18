import os
import re
import shutil
import stat
import tempfile
from email.utils import parseaddr

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


def parse_author(address):  # type: (str) -> tuple
    """Parse name and address parts from an email address string.

    >>> parse_author("John Doe <john.doe@example.com>")
    ('John Doe', 'john.doe@example.com')

    .. note::

       If the input string does not contain an ``@`` character, it is
       assumed that it represents only a name without an email address.

    :param address: the email address string to parse.
    :return: a 2-tuple with the parsed name and email address.  If a
             part is missing, ``None`` will be returned in its place.
    """
    if "@" not in address:
        return (address, None)
    name, email = parseaddr(address)
    if not name and "@" not in email:
        return (email, None)
    return (name or None, email or None)
