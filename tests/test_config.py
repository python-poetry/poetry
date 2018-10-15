import os
import pytest
import tempfile

from poetry.config import Config
from poetry.utils.toml_file import TomlFile


@pytest.fixture
def config():
    with tempfile.NamedTemporaryFile() as f:
        f.close()

        return Config(TomlFile(f.name))


def test_config_sets_the_proper_file_permissions(config):
    config.add_property("settings.virtualenvs.create", True)

    mode = oct(os.stat(str(config.file)).st_mode & 0o777)

    assert int(mode, 8) == 384
