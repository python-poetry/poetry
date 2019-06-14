import os

import pytest

from poetry.utils._compat import Path
from poetry.utils.env import Env, SystemEnv
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


def test_env_has_symlinks_on_nix(tmp_dir):
    venv_path = Path(tmp_dir) / "Virtual Env"

    Env.build_venv(str(venv_path))

    venv = VirtualEnv(venv_path)

    venv_available = False
    try:
        from venv import EnvBuilder

        venv_available = True
    except ImportError:
        pass

    if os.name != "nt" and venv_available:
        assert os.path.islink(venv.python)


@pytest.mark.parametrize(
    "create_venv, env_class", ((True, VirtualEnv), (False, SystemEnv))
)
def test_existing_venv_with_no_create_option(
    tmp_dir, environ, config, create_venv, env_class
):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    parent_path = Path(tmp_dir)
    venv_path = parent_path / ".venv"

    Env.build_venv(str(venv_path))

    config.add_property("settings.virtualenvs.create", create_venv)

    env = Env.get(cwd=parent_path)
    assert isinstance(env, env_class)
