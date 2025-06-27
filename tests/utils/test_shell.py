from __future__ import annotations

import os
import sys
import pytest
from pathlib import PurePath, PureWindowsPath
from unittest.mock import patch, MagicMock

from poetry.utils.shell import Shell
import poetry.utils.shell as shell_module



IS_WINDOWS = sys.platform.startswith("win")


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
def test_windows_shell_activation(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_env = MagicMock()
    mock_env.path = PureWindowsPath("C:/fake/venv")
    mock_env.temp_environ.return_value.__enter__.return_value = None
    mock_env.temp_environ.return_value.__exit__.return_value = None
    mock_env.execute.return_value = 0

    s = Shell("cmd", "C:/Windows/System32/cmd.exe")

    monkeypatch.setattr("shutil.get_terminal_size", lambda: os.terminal_size((80, 24)))
    monkeypatch.setattr("poetry.utils.shell.WINDOWS", True)

    with patch("pexpect.spawn") as mock_spawn:
        mock_child = MagicMock()
        mock_child.interact.return_value = None
        mock_child.exitstatus = 0
        mock_spawn.return_value = mock_child

        with pytest.raises(SystemExit) as e:
            s.activate(mock_env)

        assert e.value.code == 0


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
def test_detect_shell_fallback_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("os.name", "nt")
    monkeypatch.setenv("COMSPEC", str(PureWindowsPath("C:/Windows/System32/cmd.exe")))

    result = shell_module.detect_shell()
    assert result == ("cmd", str(PureWindowsPath("C:/Windows/System32/cmd.exe")))


def test_shell_get_raises_on_missing_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.delenv("COMSPEC", raising=False)
    monkeypatch.setattr("os.name", "posix")

    with patch("poetry.utils.shell.detect_shell", side_effect=shell_module.ShellDetectionFailure("Shell not found")):
        Shell._shell = None
        with pytest.raises(RuntimeError, match="Unable to detect the current shell"):
            Shell.get()


@pytest.mark.skipif(IS_WINDOWS, reason="pexpect.spawn is not available on Windows")
def test_shell_activate_spawn_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    s = Shell("bash", "/bin/bash")
    mock_env = MagicMock()
    mock_env.path = PurePath("/fake/venv")

    with patch("pexpect.spawn") as mock_spawn:
        mock_child = MagicMock()
        mock_child.interact.return_value = None
        mock_child.exitstatus = 1
        mock_spawn.return_value = mock_child

        with pytest.raises(SystemExit) as e:
            s.activate(mock_env)

        assert e.value.code == 1


@patch("poetry.utils.shell.detect_shell", return_value=("sh", "/bin/sh"))
def test_detect_shell_fallback_to_sh(mock_detect_shell: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHELL", "/bin/sh")
    monkeypatch.delenv("COMSPEC", raising=False)

    Shell._shell = None  # reset cached shell
    s = Shell.get()
    assert s.name in ("sh", "zsh", "bash")
    assert s.path in ("/bin/sh", "/bin/zsh", "/bin/bash")


@patch("poetry.utils.shell.detect_shell", side_effect=shell_module.ShellDetectionFailure("Shell not found"))
def test_detect_shell_raises_when_env_missing(mock_detect_shell: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.delenv("COMSPEC", raising=False)
    Shell._shell = None
    with pytest.raises(RuntimeError, match="Unable to detect the current shell"):
        Shell.get()
