from platformdirs import user_cache_dir
from platformdirs import user_config_dir
from platformdirs import user_data_dir
from platformdirs import user_data_path

from poetry.locations import CACHE_DIR
from poetry.locations import CONFIG_DIR
from poetry.locations import DATA_DIR
from poetry.locations import data_dir


def test_platformdirs_compatibility():
    assert CACHE_DIR == user_cache_dir("pypoetry", appauthor=False)
    assert DATA_DIR == user_data_dir("pypoetry", appauthor=False)
    assert CONFIG_DIR == user_config_dir("pypoetry", appauthor=False, roaming=True)
    assert data_dir() == user_data_path("pypoetry", appauthor=False, roaming=True)
