from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.utils._compat import WINDOWS


if TYPE_CHECKING:
    from cleo.testers.application_tester import ApplicationTester
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
        ("dash", ".", ""),
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

    tester.execute()

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


@pytest.mark.parametrize("verbosity", ["", "-v", "-vv", "-vvv"])
def test_no_additional_output_in_verbose_mode(
    tmp_venv: VirtualEnv,
    mocker: MockerFixture,
    app_tester: ApplicationTester,
    verbosity: str,
) -> None:
    mocker.patch("shellingham.detect_shell", return_value=("pwsh", None))
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=tmp_venv)

    # use an AppTester instead of a CommandTester to catch additional output
    app_tester.execute(f"env activate {verbosity}")

    lines = app_tester.io.fetch_output().splitlines()
    assert len(lines) == 1
