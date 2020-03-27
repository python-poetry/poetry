from __future__ import absolute_import

import os
import re

from copy import deepcopy
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional

from poetry.locations import CACHE_DIR
from poetry.utils._compat import Path
from poetry.utils._compat import basestring

from .config_source import ConfigSource
from .dict_config_source import DictConfigSource


_NOT_SET = object()


def boolean_validator(val):
    return val in {"true", "false", "1", "0"}


def boolean_normalizer(val):
    return val in ["true", "1"]


class Config(object):

    default_config = {
        "cache-dir": str(CACHE_DIR),
        "virtualenvs": {
            "create": True,
            "in-project": False,
            "path": os.path.join("{cache-dir}", "virtualenvs"),
        },
    }

    def __init__(
        self, use_environment=True, base_dir=None
    ):  # type: (bool, Optional[Path]) -> None
        self._config = deepcopy(self.default_config)
        self._use_environment = use_environment
        self._base_dir = base_dir
        self._config_source = DictConfigSource()
        self._auth_config_source = DictConfigSource()

    @property
    def name(self):
        return str(self._file.path)

    @property
    def config(self):
        return self._config

    @property
    def config_source(self):  # type: () -> ConfigSource
        return self._config_source

    @property
    def auth_config_source(self):  # type: () -> ConfigSource
        return self._auth_config_source

    def set_config_source(self, config_source):  # type: (ConfigSource) -> Config
        self._config_source = config_source

        return self

    def set_auth_config_source(self, config_source):  # type: (ConfigSource) -> Config
        self._auth_config_source = config_source

        return self

    def merge(self, config):  # type: (Dict[str, Any]) -> None
        from poetry.utils.helpers import merge_dicts

        merge_dicts(self._config, config)

    def all(self):  # type: () -> Dict[str, Any]
        def _all(config, parent_key=""):
            all_ = {}

            for key in config:
                value = self.get(parent_key + key)
                if isinstance(value, dict):
                    all_[key] = _all(config[key], parent_key=key + ".")
                    continue

                all_[key] = value

            return all_

        return _all(self.config)

    def raw(self):  # type: () -> Dict[str, Any]
        return self._config

    def get(self, setting_name, default=None):  # type: (str, Any) -> Any
        """
        Retrieve a setting value.
        """
        keys = setting_name.split(".")

        # Looking in the environment if the setting
        # is set via a POETRY_* environment variable
        if self._use_environment:
            env = "POETRY_{}".format(
                "_".join(k.upper().replace("-", "_") for k in keys)
            )
            value = os.getenv(env, _NOT_SET)
            if value is not _NOT_SET:
                return self.process(self._get_normalizer(setting_name)(value))

        value = self._config
        for key in keys:
            if key not in value:
                return self.process(default)

            value = value[key]

        return self.process(value)

    def process(self, value):  # type: (Any) -> Any
        if not isinstance(value, basestring):
            return value

        return re.sub(r"{(.+?)}", lambda m: self.get(m.group(1)), value)

    def _get_validator(self, name):  # type: (str) -> Callable
        if name in {"virtualenvs.create", "virtualenvs.in-project"}:
            return boolean_validator

        if name == "virtualenvs.path":
            return str

    def _get_normalizer(self, name):  # type: (str) -> Callable
        if name in {"virtualenvs.create", "virtualenvs.in-project"}:
            return boolean_normalizer

        if name == "virtualenvs.path":
            return lambda val: str(Path(val))

        return lambda val: val
