from __future__ import annotations

import os

from pathlib import Path

from platformdirs import user_cache_path
from platformdirs import user_config_path
from platformdirs import user_data_path


CACHE_DIR = user_cache_path("pypoetry", appauthor=False)
CONFIG_DIR = user_config_path("pypoetry", appauthor=False, roaming=True)

REPOSITORY_CACHE_DIR = CACHE_DIR / "cache" / "repositories"


def data_dir() -> Path:
    poetry_home = os.getenv("POETRY_HOME")
    if poetry_home:
        return Path(poetry_home).expanduser()

    return user_data_path("pypoetry", appauthor=False, roaming=True)
