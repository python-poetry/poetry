import os
import re

from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import Iterator
from typing import Optional
from typing import Tuple

import pytest

from poetry.config.config import Config


if TYPE_CHECKING:
    from pathlib import Path


def get_boolean_options(config: Optional[Dict[str, Any]] = None) -> str:
    if config is None:
        config = Config.default_config

    for k, v in config.items():
        if isinstance(v, bool) or v is None:
            yield k
        if isinstance(v, dict):
            for suboption in get_boolean_options(v):
                yield f"{k}.{suboption}"


@pytest.mark.parametrize(
    ("name", "value"), [("installer.parallel", True), ("virtualenvs.create", True)]
)
def test_config_get_default_value(config: Config, name: str, value: bool):
    assert config.get(name) is value


def test_config_get_processes_depended_on_values(
    config: Config, config_cache_dir: "Path"
):
    assert str(config_cache_dir / "virtualenvs") == config.get("virtualenvs.path")


def generate_environment_variable_tests() -> Iterator[Tuple[str, str, str, bool]]:
    for env_value, value in [("true", True), ("false", False)]:
        for name in get_boolean_options():
            env_var = "POETRY_{}".format(re.sub("[.-]+", "_", name).upper())
            yield name, env_var, env_value, value


@pytest.mark.parametrize(
    ("name", "env_var", "env_value", "value"),
    list(generate_environment_variable_tests()),
)
def test_config_get_from_environment_variable(
    config: Config,
    environ: Iterator[None],
    name: str,
    env_var: str,
    env_value: str,
    value: bool,
):
    os.environ[env_var] = env_value
    assert config.get(name) is value
