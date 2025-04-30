from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cleo.io.outputs.output import Verbosity

from poetry.utils._compat import WINDOWS


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.utils.env import VirtualEnv
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("env activate")


@pytest.mark.parametrize(
    "shell, command, ext",
    (
        ("bash", "source", ""),
        ("zsh", "source", ""),
        ("fish", "source", ".fish"),
        ("nu", "overlay use", ".nu"),
        ("csh", "source", ".csh"),
        ("tcsh", "source", ".csh"),
    ),
)
@pytest.mark.skipif(WINDOWS, reason="Only Unix shells")
def test_env_activate_prints_correct_script(
    tmp_venv: VirtualEnv,
    mocker: MockerFixture,
    tester: CommandTester,
    shell: str,
    command: str,
    ext: str,
) -> None:
    mocker.patch("shellingham.detect_shell", return_value=(shell, None))
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=tmp_venv)

    tester.execute(verbosity=Verbosity.VERBOSE)

    line = tester.io.fetch_output().rstrip("\n")
    assert line == f"{command} {tmp_venv.bin_dir}/activate{ext}"


@pytest.mark.parametrize(
    "shell, command, ext, prefix",
    (
        ("cmd", ".", "activate.bat", ""),
        ("pwsh", ".", "activate.ps1", "& "),
        ("powershell", ".", "activate.ps1", "& "),
    ),
)
@pytest.mark.skipif(not WINDOWS, reason="Only Windows shells")
def test_env_activate_prints_correct_script_on_windows(
    tmp_venv: VirtualEnv,
    mocker: MockerFixture,
    tester: CommandTester,
    shell: str,
    command: str,
    ext: str,
    prefix: str,
) -> None:
    mocker.patch("shellingham.detect_shell", return_value=(shell, None))
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=tmp_venv)

    tester.execute()

    line = tester.io.fetch_output().rstrip("\n")
    assert line == f'{prefix}"{tmp_venv.bin_dir / ext!s}"'
