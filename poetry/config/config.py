import os
import re

from copy import deepcopy
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional

from poetry.locations import CACHE_DIR

from .config_source import ConfigSource
from .dict_config_source import DictConfigSource


_NOT_SET = object()


def boolean_validator(val: str) -> bool:
    return val in {"true", "false", "1", "0"}


def boolean_normalizer(val: str) -> bool:
    return val in ["true", "1"]


class Config:

    default_config = {
        "cache-dir": str(CACHE_DIR),
        "virtualenvs": {
            "create": True,
            "in-project": None,
            "path": os.path.join("{cache-dir}", "virtualenvs"),
            "options": {"always-copy": False, "system-site-packages": False},
        },
        "experimental": {"new-installer": True},
        "installer": {"parallel": True},
    }

    def __init__(
        self, use_environment: bool = True, base_dir: Optional[Path] = None
    ) -> None:
        self._config = deepcopy(self.default_config)
        self._use_environment = use_environment
        self._base_dir = base_dir
        self._config_source = DictConfigSource()
        self._auth_config_source = DictConfigSource()

    @property
    def name(self) -> str:
        return str(self._file.path)

    @property
    def config(self) -> Dict:
        return self._config

    @property
    def config_source(self) -> ConfigSource:
        return self._config_source

    @property
    def auth_config_source(self) -> ConfigSource:
        return self._auth_config_source

    def set_config_source(self, config_source: ConfigSource) -> "Config":
        self._config_source = config_source

        return self

    def set_auth_config_source(self, config_source: ConfigSource) -> "Config":
        self._auth_config_source = config_source

        return self

    def merge(self, config: Dict[str, Any]) -> None:
        from poetry.utils.helpers import merge_dicts

        merge_dicts(self._config, config)

    def all(self) -> Dict[str, Any]:
        def _all(config: Dict, parent_key: str = "") -> Dict:
            all_ = {}

            for key in config:
                value = self.get(parent_key + key)
                if isinstance(value, dict):
                    if parent_key != "":
                        current_parent = parent_key + key + "."
                    else:
                        current_parent = key + "."
                    all_[key] = _all(config[key], parent_key=current_parent)
                    continue

                all_[key] = value

            return all_

        return _all(self.config)

    def raw(self) -> Dict[str, Any]:
        return self._config

    def get(self, setting_name: str, default: Any = None) -> Any:
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

    def process(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        return re.sub(r"{(.+?)}", lambda m: self.get(m.group(1)), value)

    def _get_normalizer(self, name: str) -> Callable:
        if name in {
            "virtualenvs.create",
            "virtualenvs.in-project",
            "virtualenvs.options.always-copy",
            "virtualenvs.options.system-site-packages",
            "installer.parallel",
        }:
            return boolean_normalizer

        if name == "virtualenvs.path":
            return lambda val: str(Path(val))

        return lambda val: val
