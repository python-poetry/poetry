import os

from pathlib import Path

from poetry.utils.appdirs import user_cache_dir
from poetry.utils.appdirs import user_config_dir
from poetry.utils.appdirs import user_data_dir


CACHE_DIR = user_cache_dir("pypoetry")
DATA_DIR = user_data_dir("pypoetry")
CONFIG_DIR = user_config_dir("pypoetry")

REPOSITORY_CACHE_DIR = Path(CACHE_DIR) / "cache" / "repositories"


def data_dir() -> Path:
    poetry_home = os.getenv("POETRY_HOME")
    if poetry_home:
        return Path(poetry_home).expanduser()

    return Path(user_data_dir("pypoetry", roaming=True))
