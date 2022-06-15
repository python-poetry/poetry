from __future__ import annotations

import os
import re

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from flatdict import FlatDict

from poetry.config.config import Config
from poetry.config.config import boolean_normalizer
from poetry.config.config import int_normalizer


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator


def get_options_based_on_normalizer(normalizer: Callable) -> str:
    flattened_config = FlatDict(Config.default_config, delimiter=".")

    for k in flattened_config:
        if Config._get_normalizer(k) == normalizer:
            yield k


@pytest.mark.parametrize(
    ("name", "value"), [("installer.parallel", True), ("virtualenvs.create", True)]
)
def test_config_get_default_value(config: Config, name: str, value: bool):
    assert config.get(name) is value


def test_config_get_processes_depended_on_values(
    config: Config, config_cache_dir: Path
):
    assert str(config_cache_dir / "virtualenvs") == config.get("virtualenvs.path")


def generate_environment_variable_tests() -> Iterator[tuple[str, str, str, bool]]:
    for normalizer, values in [
        (boolean_normalizer, [("true", True), ("false", False)]),
        (int_normalizer, [("4", 4), ("2", 2)]),
    ]:
        for env_value, value in values:
            for name in get_options_based_on_normalizer(normalizer=normalizer):
                env_var = "POETRY_" + re.sub("[.-]+", "_", name).upper()
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


@pytest.mark.parametrize(
    ("path_config", "expected"),
    [("~/.venvs", Path.home() / ".venvs"), ("venv", Path("venv"))],
)
def test_config_expands_tilde_for_virtualenvs_path(
    config: Config, path_config: str, expected: Path
):
    config.merge({"virtualenvs": {"path": path_config}})
    assert config.virtualenvs_path == expected
