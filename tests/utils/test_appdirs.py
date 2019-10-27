# -*- coding: utf-8 -*-

import os
import sys
from os import path

import pytest

from poetry.utils import appdirs

windows = pytest.mark.skipif(
    not (sys.platform.startswith("win") or (sys.platform == "cli" and os.name == "nt")),
    reason="tests that check Windows only behavior",
)

macos = pytest.mark.skipif(
    sys.platform != "darwin", reason="tests that check macOS only behavior"
)

unix = pytest.mark.skipif(
    sys.platform.startswith("win")
    or (sys.platform == "cli" and os.name == "nt")
    or sys.platform == "darwin",
    reason="tests that check Unix type behavior",
)

macos_and_unix = pytest.mark.skipif(
    sys.platform.startswith("win") or (sys.platform == "cli" and os.name == "nt"),
    reason="tests that check either Unix or macOS behavior",
)


@macos_and_unix
def test_poetry_home_defined_by_env_var():
    crazy_dir = path.join(os.environ["HOME"], "my_crazy_dir")
    os.environ["POETRY_HOME"] = crazy_dir
    assert appdirs.poetry_home_dir() == crazy_dir
    del os.environ["POETRY_HOME"]


@macos_and_unix
def test_poetry_home_defined_by_xdg():
    xdg_package_home = path.join(os.environ["HOME"], ".local", "opt")
    poetry_home = path.join(xdg_package_home, "poetry")
    os.environ["XDG_PACKAGE_HOME"] = xdg_package_home
    assert appdirs.poetry_home_dir() == poetry_home
    del os.environ["XDG_PACKAGE_HOME"]


@macos_and_unix
def test_poetry_home_fallback_default():
    poetry_home = path.join(os.environ["HOME"], ".poetry")
    assert appdirs.poetry_home_dir() == poetry_home


@macos_and_unix
def test_user_cache_dir_xdg_set():
    xdg_cache_home = path.join(os.environ["HOME"], ".local", "var", "cache")
    poetry_cache = path.join(xdg_cache_home, "poetry")
    os.environ["XDG_CACHE_HOME"] = xdg_cache_home
    assert appdirs.user_cache_dir("poetry") == poetry_cache
    del os.environ["XDG_CACHE_HOME"]


@macos
def test_user_cache_dir_macos_default():
    poetry_cache = path.join(appdirs.expanduser("~/Library/Caches"), "poetry")
    if "XDG_CACHE_HOME" in os.environ:
        del os.environ["XDG_CACHE_HOME"]
    assert appdirs.user_cache_dir("poetry") == poetry_cache


@unix
def test_user_cache_dir_unix_default():
    poetry_cache = path.join(appdirs.expanduser("~/.cache"), "poetry")
    if "XDG_CACHE_HOME" in os.environ:
        del os.environ["XDG_CACHE_HOME"]
    assert appdirs.user_cache_dir("poetry") == poetry_cache


@macos_and_unix
def test_user_data_dir_xdg_set():
    xdg_data_home = path.join(os.environ["HOME"], ".local", "crazy_path", "data")
    poetry_data = path.join(xdg_data_home, "poetry")
    os.environ["XDG_DATA_HOME"] = xdg_data_home
    assert appdirs.user_data_dir("poetry") == poetry_data
    del os.environ["XDG_DATA_HOME"]


@macos
def test_user_data_dir_macos_default():
    poetry_data = path.join(
        appdirs.expanduser("~/Library/Application Support"), "poetry"
    )
    if "XDG_DATA_HOME" in os.environ:
        del os.environ["XDG_DATA_HOME"]
    assert appdirs.user_data_dir("poetry") == poetry_data


@unix
def test_user_data_dir_unix_default():
    poetry_data = path.join(appdirs.expanduser("~/.local/share"), "poetry")
    if "XDG_DATA_HOME" in os.environ:
        del os.environ["XDG_DATA_HOME"]
    assert appdirs.user_data_dir("poetry") == poetry_data


@macos_and_unix
def test_user_config_dir_xdg_set():
    xdg_config_home = path.join(os.environ["HOME"], ".local", "crazy_path", "data")
    poetry_config = path.join(xdg_config_home, "poetry")
    os.environ["XDG_CONFIG_HOME"] = xdg_config_home
    assert appdirs.user_config_dir("poetry") == poetry_config
    del os.environ["XDG_CONFIG_HOME"]


@macos
def test_user_config_dir_macos_default():
    poetry_data = path.join(
        appdirs.expanduser("~/Library/Application Support"), "poetry"
    )
    if "XDG_CONFIG_HOME" in os.environ:
        del os.environ["XDG_CONFIG_HOME"]
    assert appdirs.user_config_dir("poetry") == poetry_data


@unix
def test_user_config_dir_unix_default():
    poetry_data = path.join(appdirs.expanduser("~/.config"), "poetry")
    if "XDG_CONFIG_HOME" in os.environ:
        del os.environ["XDG_CONFIG_HOME"]
    assert appdirs.user_config_dir("poetry") == poetry_data


@macos
def test_site_config_dirs_xdg_set_macos():
    site_config_dirs = [
        appdirs.expanduser("~/.local/config.d"),
        appdirs.expanduser("~/.config/others.d"),
    ]
    os.environ["XDG_CONFIG_DIRS"] = os.pathsep.join(site_config_dirs)

    for expected, actual in zip(
        [path.join(x, "poetry") for x in site_config_dirs],
        appdirs.site_config_dirs("poetry"),
    ):
        assert expected == actual

    del os.environ["XDG_CONFIG_DIRS"]


@macos
def test_site_config_dirs_macos_default():
    site_config_dirs = [
        path.join(appdirs.expanduser("~/Library/Application Support"), "poetry")
    ]
    if "XDG_CONFIG_DIRS" in os.environ:
        del os.environ["XDG_CONFIG_DIRS"]
    for expected, actual in zip(site_config_dirs, appdirs.site_config_dirs("poetry")):
        assert expected == actual


@unix
def test_site_config_dirs_xdg_set_unix():
    site_config_dirs = [
        appdirs.expanduser("~/.local/config.d"),
        appdirs.expanduser("~/.config/others.d"),
    ]
    os.environ["XDG_CONFIG_DIRS"] = os.pathsep.join(site_config_dirs)
    site_config_dirs.append("/etc")

    for expected, actual in zip(
        [path.join(x, "poetry") for x in site_config_dirs],
        appdirs.site_config_dirs("poetry"),
    ):
        assert expected == actual

    del os.environ["XDG_CONFIG_DIRS"]


@unix
def test_site_config_dirs_unix_default():
    site_config_dirs = ["/etc/xdg/poetry", "/etc/poetry"]
    if "XDG_CONFIG_DIRS" in os.environ:
        del os.environ["XDG_CONFIG_DIRS"]
    for expected, actual in zip(site_config_dirs, appdirs.site_config_dirs("poetry")):
        assert expected == actual
