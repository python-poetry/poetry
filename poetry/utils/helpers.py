import os
import re
import shutil
import tempfile
from collections import Mapping

from contextlib import contextmanager
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


def parse_requires(requires):  # type: (str) -> Union[list, None]
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

    if requires_dist:
        return requires_dist


def get_http_basic_auth(repository_name):  # type: (str) -> tuple
    config = Config.create("auth.toml")
    repo_auth = config.setting("http-basic.{}".format(repository_name))
    if repo_auth:
        return repo_auth["username"], repo_auth["password"]
    return None


# If the string can be expanded by a call to os.environ.get, then we
# return that string.  Otherwise, we return the original escaped string.
def __maybe_expand_env_var(match): # type: (SRE.Match) -> str
    string = match.group(0)
    
    stripped = string[2:-1] # remove environment variable escaping

    value_from_env = os.environ.get(stripped)
    if value_from_env is not None:
        return value_from_env

    return string


# If the argument to this function is a string, we check if it contains
# an environment escape sequence and expand it.  If it's a dict, instead
# we expand it.
def __expand_env_vars(obj): # type (object) -> object
    if isinstance(obj, Mapping): # obj is dict-like
        return expand_environment_vars(obj)
    elif isinstance(obj, list):
        return list(map(__expand_env_vars, obj))
    elif isinstance(obj, str):
        env_escape_pat = "(${[^$]+})"
        return re.sub(env_escape_pat, __maybe_expand_env_var, str(obj))
    else:
        return obj
    

def expand_environment_vars(toml_data): # type: (dict) -> dict
    res = {k: __expand_env_vars(v) for k, v in toml_data.items()}
    return res
