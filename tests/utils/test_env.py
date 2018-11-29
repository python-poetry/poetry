import os

import pytest

from poetry.utils._compat import Path
from poetry.utils.env import Env
from poetry.utils.env import VirtualEnv


def test_virtualenvs_with_spaces_in_their_path_work_as_expected(tmp_dir):
    venv_path = Path(tmp_dir) / "Virtual Env"

    Env.build_venv(str(venv_path))

    venv = VirtualEnv(venv_path)

    assert venv.run("python", "-V", shell=True).startswith("Python")


def test_env_get_in_project_venv(tmp_dir, environ):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    (Path(tmp_dir) / ".venv").mkdir()

    venv = Env.get(cwd=Path(tmp_dir))

    assert venv.path == Path(tmp_dir) / ".venv"
    assert venv.is_sane()


def test_env_get_in_project_venv_as_file(tmp_dir, environ):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    open(str(Path(tmp_dir) / ".venv"), "w")

    with pytest.raises(AssertionError, match=".venv should be a directory"):
        Env.get(cwd=Path(tmp_dir))


def test_env_get_in_project_venv_as_not_empty_directory(tmp_dir, environ):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    (Path(tmp_dir) / ".venv").mkdir()
    open(str(Path(tmp_dir) / ".venv/test_file"), "w")

    with pytest.raises(
        AssertionError, match=".venv should be empty if not a virtual environment"
    ):
        Env.get(cwd=Path(tmp_dir))
