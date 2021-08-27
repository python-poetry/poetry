import os

from pathlib import Path
<<<<<<< HEAD
from typing import TYPE_CHECKING
from typing import Iterator
from typing import List
=======
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

import pytest

from poetry.utils.env import EnvManager


<<<<<<< HEAD
if TYPE_CHECKING:
    from tests.helpers import PoetryTestApplication


@pytest.fixture
def venv_name(app: "PoetryTestApplication") -> str:
=======
@pytest.fixture
def venv_name(app):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return EnvManager.generate_env_name("simple-project", str(app.poetry.file.parent))


@pytest.fixture
<<<<<<< HEAD
def venv_cache(tmp_dir: str) -> Path:
=======
def venv_cache(tmp_dir):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return Path(tmp_dir)


@pytest.fixture(scope="module")
<<<<<<< HEAD
def python_versions() -> List[str]:
=======
def python_versions():
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    return ["3.6", "3.7"]


@pytest.fixture
<<<<<<< HEAD
def venvs_in_cache_config(app: "PoetryTestApplication", venv_cache: Path) -> None:
=======
def venvs_in_cache_config(app, venv_cache):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    app.poetry.config.merge({"virtualenvs": {"path": str(venv_cache)}})


@pytest.fixture
def venvs_in_cache_dirs(
<<<<<<< HEAD
    app: "PoetryTestApplication",
    venvs_in_cache_config: None,
    venv_name: str,
    venv_cache: Path,
    python_versions: List[str],
) -> List[str]:
    directories = []
    for version in python_versions:
        directory = venv_cache.joinpath(f"{venv_name}-py{version}")
=======
    app, venvs_in_cache_config, venv_name, venv_cache, python_versions
):
    directories = []
    for version in python_versions:
        directory = venv_cache.joinpath("{}-py{}".format(venv_name, version))
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
        directory.mkdir(parents=True, exist_ok=True)
        directories.append(directory.name)
    return directories


@pytest.fixture
<<<<<<< HEAD
def venvs_in_project_dir(app: "PoetryTestApplication") -> Iterator[Path]:
=======
def venvs_in_project_dir(app):
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
    os.environ.pop("VIRTUAL_ENV", None)
    venv_dir = app.poetry.file.parent.joinpath(".venv")
    venv_dir.mkdir(exist_ok=True)
    app.poetry.config.merge({"virtualenvs": {"in-project": True}})

    try:
        yield venv_dir
    finally:
        venv_dir.rmdir()
