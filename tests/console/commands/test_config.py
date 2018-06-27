import pytest
import tempfile

from cleo.testers import CommandTester

from poetry.config import Config
from poetry.utils._compat import Path
from poetry.utils.toml_file import TomlFile


@pytest.fixture
def config():
    with tempfile.NamedTemporaryFile() as f:
        f.close()

        return Config(TomlFile(f.name))


def test_list_displays_default_value_if_not_set(app, config):
    command = app.find("config")
    command._config = config
    tester = CommandTester(command)

    tester.execute([("command", command.get_name()), ("--list", True)])

    expected = """settings.virtualenvs.create = true
settings.virtualenvs.in-project = false
repositories = {}
"""

    assert tester.get_display(True) == expected


def test_list_displays_set_get_setting(app, config):
    command = app.find("config")
    command._config = config
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
repositories = {}
"""

    assert tester.get_display(True) == expected
