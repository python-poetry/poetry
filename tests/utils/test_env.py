import os

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
