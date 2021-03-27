import os

from pathlib import Path

import pytest

from poetry.utils.env import EnvManager


@pytest.fixture
def venv_name(app):
    return EnvManager.generate_env_name("simple-project", str(app.poetry.file.parent))


@pytest.fixture
def venv_cache(tmp_dir):
    return Path(tmp_dir)


@pytest.fixture(scope="module")
def python_versions():
    return ["3.6", "3.7"]


@pytest.fixture
def venvs_in_cache_config(app, venv_cache):
    app.poetry.config.merge({"virtualenvs": {"path": str(venv_cache)}})


@pytest.fixture
def venvs_in_cache_dirs(
    app, venvs_in_cache_config, venv_name, venv_cache, python_versions
):
    directories = []
    for version in python_versions:
        directory = venv_cache.joinpath("{}-py{}".format(venv_name, version))
        directory.mkdir(parents=True, exist_ok=True)
        directories.append(directory.name)
    return directories


@pytest.fixture
def venvs_in_project_dir(app):
    os.environ.pop("VIRTUAL_ENV", None)
    venv_dir = app.poetry.file.parent.joinpath(".venv")
    venv_dir.mkdir(exist_ok=True)
    app.poetry.config.merge({"virtualenvs": {"in-project": True}})

    try:
        yield venv_dir
    finally:
        venv_dir.rmdir()
