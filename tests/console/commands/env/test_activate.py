from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.console.commands.env.activate import EnvActivateCommand
from poetry.console.commands.env.activate import ShellNotSupportedError
from poetry.utils._compat import WINDOWS


if TYPE_CHECKING:
    from cleo.testers.application_tester import ApplicationTester
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.utils.env import VirtualEnv
    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(
    command_tester_factory: CommandTesterFactory, tmp_venv: VirtualEnv
) -> CommandTester:
    tester = command_tester_factory("env activate")
    assert isinstance(tester.command, EnvActivateCommand)
    tester.command.set_env(tmp_venv)
    return tester


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
def test_env_activate_prints_correct_script(
    tmp_venv: VirtualEnv,
    mocker: MockerFixture,
    tester: CommandTester,
    shell: str,
    command: str,
    ext: str,
) -> None:
    mocker.patch("shellingham.detect_shell", return_value=(shell, None))

    if WINDOWS and shell in {"csh", "tcsh"}:
        with pytest.raises(ShellNotSupportedError):
            tester.execute()

    else:
        tester.execute()

        line = tester.io.fetch_output().rstrip("\n")
        assert line == f"{command} {tmp_venv.bin_dir.as_posix()}/activate{ext}"


@pytest.mark.parametrize(
    "shell, command, ext, quote",
    (
        ("cmd", "", ".bat", '"'),
        ("pwsh", "&", ".ps1", "'"),
        ("powershell", "&", ".ps1", "'"),
    ),
)
@pytest.mark.skipif(not WINDOWS, reason="Only Windows shells")
def test_env_activate_prints_correct_script_for_windows_shells(
    tmp_venv: VirtualEnv,
    mocker: MockerFixture,
    tester: CommandTester,
    shell: str,
    command: str,
    ext: str,
    quote: str,
) -> None:
    mocker.patch("shellingham.detect_shell", return_value=(shell, None))

    tester.execute()

    line = tester.io.fetch_output().rstrip("\n")
    activation_script = tmp_venv.bin_dir / f"activate{ext}"
    assert line == f"{command} {quote}{activation_script}{quote}".strip()


@pytest.mark.parametrize("shell", ["powershell", "pwsh"])
@pytest.mark.parametrize("windows", [False, True])
@pytest.mark.parametrize(
    "directory, quoted_directory",
    [
        ("simple", "simple"),
        ("with spaces", "with spaces"),
        ("$variable", "$variable"),
        ("$(1+1)", "$(1+1)"),
        ("back`tick", "back`tick"),
        ("it's", "it''s"),
        ("it\u2018s", "it\u2018\u2018s"),
        ("it\u2019s", "it\u2019\u2019s"),
        ("it\u201as", "it\u201a\u201as"),
        ("it\u201bs", "it\u201b\u201bs"),
    ],
)
def test_env_activate_quotes_powershell_paths(
    mocker: MockerFixture,
    shell: str,
    windows: bool,
    directory: str,
    quoted_directory: str,
) -> None:
    mocker.patch("poetry.console.commands.env.activate.WINDOWS", windows)
    activation_script = Path(directory) / "activate.ps1"
    expected_path = Path(quoted_directory) / "activate.ps1"

    assert EnvActivateCommand._quote(activation_script, shell) == f"'{expected_path}'"


@pytest.mark.parametrize("verbosity", ["", "-v", "-vv", "-vvv"])
def test_no_additional_output_in_verbose_mode(
    tmp_venv: VirtualEnv,
    mocker: MockerFixture,
    app_tester: ApplicationTester,
    verbosity: str,
) -> None:
    mocker.patch("shellingham.detect_shell", return_value=("pwsh", None))
    mocker.patch("poetry.utils.env.EnvManager.create_venv", return_value=tmp_venv)

    # use an AppTester instead of a CommandTester to catch additional output
    app_tester.execute(f"env activate {verbosity}")

    lines = app_tester.io.fetch_output().splitlines()
    assert len(lines) == 1


def test_env_activate_uses_configured_environment(
    tmp_venv: VirtualEnv,
    mocker: MockerFixture,
    tester: CommandTester,
) -> None:
    mocker.patch("shellingham.detect_shell", return_value=("bash", None))
    get_env = mocker.patch(
        "poetry.utils.env.EnvManager.get",
        side_effect=AssertionError("env activate should use the configured env"),
    )

    tester.execute()

    assert not get_env.called
    line = tester.io.fetch_output().rstrip("\n")
    assert line == f"source {tmp_venv.bin_dir.as_posix()}/activate"
