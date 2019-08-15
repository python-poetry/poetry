import os
import pytest
import shutil

from poetry.utils._compat import Path
from poetry.utils.env import Env
from poetry.utils.env import VirtualEnv
from poetry.utils.env import EnvCommandError

MINIMAL_SCRIPT = """\

print("Minimal Output"),
"""

# Script expected to fail.
ERRORING_SCRIPT = """\
import nullpackage

print("nullpackage loaded"),
"""


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

    shutil.rmtree(str(venv.path))


@pytest.fixture
def tmp_venv(tmp_dir, request):
    venv_path = Path(tmp_dir) / "venv"

    Env.build_venv(str(venv_path))

    venv = VirtualEnv(venv_path)
    yield venv

    shutil.rmtree(str(venv.path))


def test_env_has_symlinks_on_nix(tmp_dir, tmp_venv):
    venv_available = False
    try:
        from venv import EnvBuilder

        venv_available = True
    except ImportError:
        pass

    if os.name != "nt" and venv_available:
        assert os.path.islink(tmp_venv.python)


def test_run_with_input(tmp_dir, tmp_venv):
    result = tmp_venv.run("python", "-", input_=MINIMAL_SCRIPT)

    assert result == "Minimal Output" + os.linesep


def test_run_with_input_non_zero_return(tmp_dir, tmp_venv):

    with pytest.raises(EnvCommandError) as processError:

        # Test command that will return non-zero returncode.
        result = tmp_venv.run("python", "-", input_=ERRORING_SCRIPT)

    assert processError.value.e.returncode == 1
