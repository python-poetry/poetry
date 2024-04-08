from __future__ import annotations

import os
import re

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

from poetry.config.config import Config
from poetry.config.config import boolean_normalizer
from poetry.config.config import int_normalizer
from poetry.utils.password_manager import PasswordManager
from tests.helpers import flatten_dict


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator

    from tests.conftest import DummyBackend

    Normalizer = Callable[[str], Any]


def get_options_based_on_normalizer(normalizer: Normalizer) -> Iterator[str]:
    flattened_config = flatten_dict(obj=Config.default_config, delimiter=".")

    for k in flattened_config:
        if Config._get_normalizer(k) == normalizer:
            yield k


@pytest.mark.parametrize(
    ("name", "value"), [("installer.parallel", True), ("virtualenvs.create", True)]
)
def test_config_get_default_value(config: Config, name: str, value: bool) -> None:
    assert config.get(name) is value


def test_config_get_processes_depended_on_values(
    config: Config, config_cache_dir: Path
) -> None:
    assert str(config_cache_dir / "virtualenvs") == config.get("virtualenvs.path")


def generate_environment_variable_tests() -> Iterator[tuple[str, str, str, bool]]:
    data: list[tuple[Normalizer, list[tuple[str, Any]]]] = [
        (boolean_normalizer, [("true", True), ("false", False)]),
        (int_normalizer, [("4", 4), ("2", 2)]),
    ]

    for normalizer, values in data:
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
) -> None:
    os.environ[env_var] = env_value
    assert config.get(name) is value


def test_config_get_from_environment_variable_nested(
    config: Config,
    environ: Iterator[None],
) -> None:
    options = config.default_config["virtualenvs"]["options"]
    expected = {}

    for k, v in options.items():
        if isinstance(v, bool):
            expected[k] = not v
            os.environ[f"POETRY_VIRTUALENVS_OPTIONS_{k.upper().replace('-', '_')}"] = (
                "true" if expected[k] else "false"
            )

    assert config.get("virtualenvs.options") == expected


@pytest.mark.parametrize(
    ("path_config", "expected"),
    [("~/.venvs", Path.home() / ".venvs"), ("venv", Path("venv"))],
)
def test_config_expands_tilde_for_virtualenvs_path(
    config: Config, path_config: str, expected: Path
) -> None:
    config.merge({"virtualenvs": {"path": path_config}})
    assert config.virtualenvs_path == expected


def test_disabled_keyring_is_unavailable(
    config: Config, with_simple_keyring: None, dummy_keyring: DummyBackend
) -> None:
    manager = PasswordManager(config)
    assert manager.use_keyring

    config.config["keyring"]["enabled"] = False
    manager = PasswordManager(config)
    assert not manager.use_keyring
