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


def test_list_displays_default_value_if_not_set(app, config):
    command = app.find("config")
    command._config = Config(config.file)
    tester = CommandTester(command)

    tester.execute([("command", command.get_name()), ("--list", True)])

    expected = """settings.virtualenvs.create = true
settings.virtualenvs.in-project = false
settings.virtualenvs.path = "."
repositories = {}
"""

    assert tester.get_display(True) == expected


def test_list_displays_set_get_setting(app, config):
    command = app.find("config")
    command._config = Config(config.file)
    tester = CommandTester(command)

    tester.execute(
        [
            ("command", command.get_name()),
            ("key", "settings.virtualenvs.create"),
            ("value", ["false"]),
        ]
    )

    command._config = Config(config.file)
    tester.execute([("command", command.get_name()), ("--list", True)])

    expected = """settings.virtualenvs.create = false
settings.virtualenvs.in-project = false
settings.virtualenvs.path = "."
repositories = {}
"""

    assert tester.get_display(True) == expected


def test_display_single_setting(app, config):
    command = app.find("config")
    command._config = Config(config.file)
    tester = CommandTester(command)

    tester.execute(
        [("command", command.get_name()), ("key", "settings.virtualenvs.create")]
    )

    expected = """true
"""

    assert tester.get_display(True) == expected
