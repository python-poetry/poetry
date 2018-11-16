from poetry.utils._compat import Path
from poetry.utils.env import Env
from poetry.utils.env import VirtualEnv


def test_virtualenvs_with_spaces_in_their_path_work_as_expected(tmp_dir):
    venv_path = Path(tmp_dir) / "Virtual Env"

    Env.build_venv(str(venv_path))

    venv = VirtualEnv(venv_path)

    assert venv.run("python", "-V", shell=True).startswith("Python")
