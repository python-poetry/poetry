from poetry.utils.env import Env
from poetry.utils._compat import Path
import sys


def test_execute_windows_calls_exe(mocker):
    sys.platform = "win32"
    subprocess_call = mocker.patch("subprocess.call")
    Env(Path("/")).execute("test")
    assert subprocess_call.call_args[0][0][0].endswith("/test.exe")


def test_execute_non_windows_ignores_exe(mocker):
    sys.platform = "linux"
    subprocess_call = mocker.patch("subprocess.call")
    Env(Path("/")).execute("test")
    called_path = subprocess_call.call_args
    assert subprocess_call.call_args[0][0][0].endswith("/test")


def test_execute_non_windows_does_not_stem_input(mocker):
    sys.platform = "linux"
    subprocess_call = mocker.patch("subprocess.call")
    Env(Path("/")).execute("test.test")
    assert subprocess_call.call_args[0][0][0].endswith("/test.test")
