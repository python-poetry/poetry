
import sys

from poetry.utils import venv


def test_venv_run_on_windows_with_paths_with_spaces(tmpdir):
    if sys.platform != "win32":
        return

    venvdir = tmpdir / "folder name with spaces"
    venvdir = str(venvdir.dirpath())
    venv.Venv.build(venvdir)
    _venv = venv.Venv(venvdir)

    _venv.run("pip", "list")
    _venv.run("pip", "list", shell=True)
    _venv.run("python", "-c" "\"print('Goodbye, Bugs!')\"")
    _venv.run("python", "-c", "\"print('Goodbye, Bugs!')\"", shell=True)
