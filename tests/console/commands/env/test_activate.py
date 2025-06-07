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


@pytest.mark.parametrize(
    "shell, ext, expected_prefix",
    (
        ("cmd", "activate.bat", ""),
        ("pwsh", "activate.ps1", "& "),
        ("powershell", "activate.ps1", "& "),
    ),
)
@pytest.mark.skipif(not WINDOWS, reason="Only Windows shells")
def test_env_activate_windows_shells_get_quoted_path_only(
    tmp_venv: VirtualEnv,
    mocker: MockerFixture,
    tester: CommandTester,
    shell: str,
    ext: str,
    expected_prefix: str,
) -> None:
    mocker.patch("shellingham.detect_shell", return_value=(shell, None))
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=tmp_venv)

    tester.execute()

    line = tester.io.fetch_output().rstrip("\n")
    expected = f'{expected_prefix}"{tmp_venv.bin_dir / ext!s}"'
    assert line == expected


@pytest.mark.parametrize(
    "shell, command, ext",
    (
        ("bash", "source", ""),
        ("zsh", "source", ""),
        ("fish", "source", ".fish"),
        ("nu", "overlay use", ".nu"),
        pytest.param(
            "csh",
            "source",
            ".csh",
            marks=pytest.mark.skipif(
                WINDOWS, reason="csh activator not created on Windows"
            ),
        ),
        pytest.param(
            "tcsh",
            "source",
            ".csh",
            marks=pytest.mark.skipif(
                WINDOWS, reason="tcsh activator not created on Windows"
            ),
        ),
        ("sh", "source", ""),
    ),
)
def test_env_activate_unix_shells_get_command_with_path(
    tmp_venv: VirtualEnv,
    mocker: MockerFixture,
    tester: CommandTester,
    shell: str,
    command: str,
    ext: str,
) -> None:
    mocker.patch("shellenv.detect_shell", return_value=(shell, None))
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=tmp_venv)

    tester.execute()

    line = tester.io.fetch_output().rstrip("\n")
    expected_path = f"{tmp_venv.bin_dir}/activate{ext}"
    if WINDOWS:
        import shlex

        quoted_path = shlex.quote(str(tmp_venv.bin_dir / f"activate{ext}"))
        expected = f"{command} {quoted_path}"
    else:
        expected = f"{command} {expected_path}"

    assert line == expected


def test_env_activate_bash_on_windows_gets_source_command(
    tmp_venv: VirtualEnv,
    mocker: MockerFixture,
    tester: CommandTester,
) -> None:
    mocker.patch("shellingham.detect_shell", return_value=("bash", None))
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=tmp_venv)

    mocker.patch("poetry.console.commands.env.activate.WINDOWS", True)

    tester.execute()

    line = tester.io.fetch_output().rstrip("\n")

    assert line.startswith("source ")
    assert "activate" in line
    assert not (line.startswith('"') and line.endswith('"') and "source" not in line)


def test_env_activate_unknown_shell_defaults_to_source(
    tmp_venv: VirtualEnv,
    mocker: MockerFixture,
    tester: CommandTester,
) -> None:
    mocker.patch("shellingham.detect_shell", return_value=("unknown_shell", None))
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=tmp_venv)

    tester.execute()

    line = tester.io.fetch_output().rstrip("\n")
    assert line.startswith("source ")


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
