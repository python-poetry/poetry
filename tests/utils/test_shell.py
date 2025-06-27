import sys
import pytest
from pathlib import PureWindowsPath

@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
def test_detect_shell_fallback_windows(monkeypatch):
    monkeypatch.setattr("os.name", "nt")
    monkeypatch.setenv("COMSPEC", str(PureWindowsPath("C:/Windows/System32/cmd.exe")))

    from poetry.utils import shell
    result = shell.detect_shell()
    assert result == ("cmd", str(PureWindowsPath("C:/Windows/System32/cmd.exe")))
