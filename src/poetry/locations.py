from __future__ import annotations

import logging
import os

from pathlib import Path

from platformdirs import user_cache_path
from platformdirs import user_config_path
from platformdirs import user_data_path


logger = logging.getLogger(__name__)

_APP_NAME = "pypoetry"

DEFAULT_CACHE_DIR = user_cache_path(_APP_NAME, appauthor=False)
CONFIG_DIR = Path(
    os.getenv("POETRY_CONFIG_DIR")
    or user_config_path(_APP_NAME, appauthor=False, roaming=True)
)


def data_dir() -> Path:
    poetry_home = os.getenv("POETRY_HOME")
    if poetry_home:
        return Path(poetry_home).expanduser()

    return user_data_path(_APP_NAME, appauthor=False, roaming=True)
