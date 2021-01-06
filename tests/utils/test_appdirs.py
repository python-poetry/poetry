from os import environ
from os import path
from sys import platform

from poetry.utils.appdirs import WINDOWS
from poetry.utils.appdirs import expanduser
from poetry.utils.appdirs import user_cache_dir
from poetry.utils.appdirs import user_config_dir
from poetry.utils.appdirs import user_data_dir


def test_user_cache_dir():
    if WINDOWS or (platform == "darwin"):
        return

    environ["POETRY_HOME"] = "/poetry"
    environ["XDG_CACHE_HOME"] = "/xdg/.cache"
    appname = "pypoetry"
    default_user_cache_dir = path.join(expanduser("~/.cache"), appname)

    assert user_cache_dir(appname) == path.join(
        environ["POETRY_HOME"], ".cache", appname
    )

    del environ["POETRY_HOME"]
    assert user_cache_dir(appname) == path.join(environ["XDG_CACHE_HOME"], appname)

    del environ["XDG_CACHE_HOME"]
    assert user_cache_dir(appname) == default_user_cache_dir


def test_user_config_dir():
    if WINDOWS or (platform == "darwin"):
        return

    environ["POETRY_HOME"] = "/poetry"
    environ["XDG_CONFIG_HOME"] = "/xdg/.config"
    appname = "pypoetry"
    default_user_config_dir = path.join(expanduser("~/.config"), appname)

    assert user_config_dir(appname) == path.join(
        environ["POETRY_HOME"], ".config", appname
    )

    del environ["POETRY_HOME"]
    assert user_config_dir(appname) == path.join(environ["XDG_CONFIG_HOME"], appname)

    del environ["XDG_CONFIG_HOME"]
    assert user_config_dir(appname) == default_user_config_dir


def test_user_data_dir():
    if WINDOWS or (platform == "darwin"):
        return

    environ["POETRY_HOME"] = "/poetry"
    environ["XDG_DATA_HOME"] = "/xdg/.local/share"
    appname = "pypoetry"
    default_user_data_dir = path.join(expanduser("~/.local/share"), appname)

    assert user_data_dir(appname) == path.join(
        environ["POETRY_HOME"], ".local/share", appname
    )

    del environ["POETRY_HOME"]
    assert user_data_dir(appname) == path.join(environ["XDG_DATA_HOME"], appname)

    del environ["XDG_DATA_HOME"]
    assert user_data_dir(appname) == default_user_data_dir
