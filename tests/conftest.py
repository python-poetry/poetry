import pytest
import tempfile

from poetry.config import Config
from poetry.utils.toml_file import TomlFile


@pytest.fixture
def config():  # type: () -> Config
    with tempfile.NamedTemporaryFile() as f:
        f.close()

        return Config(TomlFile(f.name))
