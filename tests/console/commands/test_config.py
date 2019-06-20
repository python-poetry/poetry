import os
import pytest
import tempfile

from cleo.testers import CommandTester

from poetry.config import Config
from poetry.utils.toml_file import TomlFile


@pytest.fixture
def config():
    with tempfile.NamedTemporaryFile() as f:
        f.close()

        return Config(TomlFile(f.name))


@pytest.fixture(autouse=True)
def setup(config):
    config.add_property("settings.virtualenvs.path", ".")

    yield

    config.remove_property("settings.virtualenvs.path")


@pytest.fixture()
def nonexistent_config_path():
    config_file_path = os.path.join(tempfile.gettempdir(), "pypoetry", "config.toml")
    if os.path.exists(config_file_path):
        os.unlink(config_file_path)
    if os.path.exists(os.path.basename(config_file_path)):
        os.rmdir(os.path.basename(config_file_path))
    return config_file_path


def test_list_displays_default_value_if_not_set(app, config):
    command = app.find("config")
    command._settings_config = Config(config.file)
    tester = CommandTester(command)

    tester.execute("--list")

    expected = """settings.virtualenvs.create = true
settings.virtualenvs.in-project = false
settings.virtualenvs.path = "."
repositories = {}
"""

    assert expected == tester.io.fetch_output()


def test_list_displays_set_get_setting(app, config):
    command = app.find("config")
    command._settings_config = Config(config.file)
    tester = CommandTester(command)

    tester.execute("settings.virtualenvs.create false")

    command._settings_config = Config(config.file)
    tester.execute("--list")

    expected = """settings.virtualenvs.create = false
settings.virtualenvs.in-project = false
settings.virtualenvs.path = "."
repositories = {}
"""

    assert expected == tester.io.fetch_output()


def test_display_single_setting(app, config):
    command = app.find("config")
    command._settings_config = Config(config.file)
    tester = CommandTester(command)

    tester.execute("settings.virtualenvs.create")

    expected = """true
"""

    assert expected == tester.io.fetch_output()


def test_autocreate_config_directory(app, nonexistent_config_path):
    command = app.find("config")

    command._settings_config = Config(TomlFile(nonexistent_config_path))

    tester = CommandTester(command)
    tester.execute("settings.virtualenvs.create false")

    assert "" == tester.io.fetch_output()

    tester = CommandTester(command)
    tester.execute("settings.virtualenvs.create")

    expected = """false
"""
    assert expected == tester.io.fetch_output()
