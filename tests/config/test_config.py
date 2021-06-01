import os

import pytest


@pytest.mark.parametrize(
    ("name", "value"), [("installer.parallel", True), ("virtualenvs.create", True)]
)
def test_config_get_default_value(config, name, value):
    assert config.get(name) is value


def test_config_get_processes_depended_on_values(config, config_cache_dir):
    assert str(config_cache_dir / "virtualenvs") == config.get("virtualenvs.path")


@pytest.mark.parametrize(
    ("name", "env_value", "value"),
    [
        ("installer.parallel", "true", True),
        ("installer.parallel", "false", False),
        ("virtualenvs.create", "true", True),
        ("virtualenvs.create", "false", False),
    ],
)
def test_config_get_from_environment_variable(config, environ, name, env_value, value):
    env_var = "POETRY_{}".format("_".join(k.upper() for k in name.split(".")))
    os.environ[env_var] = env_value
    assert config.get(name) is value
