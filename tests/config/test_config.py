import os
import re

import pytest

from poetry.config.config import Config


def get_boolean_options(config=None):
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
def test_config_get_default_value(config, name, value):
    assert config.get(name) is value


def test_config_get_processes_depended_on_values(config, config_cache_dir):
    assert str(config_cache_dir / "virtualenvs") == config.get("virtualenvs.path")


def generate_environment_variable_tests():
    for env_value, value in [("true", True), ("false", False)]:
        for name in get_boolean_options():
            env_var = "POETRY_{}".format(re.sub("[.-]+", "_", name).upper())
            yield (name, env_var, env_value, value)


@pytest.mark.parametrize(
    ("name", "env_var", "env_value", "value"),
    list(generate_environment_variable_tests()),
)
def test_config_get_from_environment_variable(
    config, environ, name, env_var, env_value, value
):
    os.environ[env_var] = env_value
    assert config.get(name) is value
