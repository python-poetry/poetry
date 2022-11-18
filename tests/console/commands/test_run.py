from __future__ import annotations

import subprocess

from typing import TYPE_CHECKING

import pytest

from poetry.utils._compat import WINDOWS


if TYPE_CHECKING:
    from cleo.testers.application_tester import ApplicationTester
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from poetry.poetry import Poetry
    from poetry.utils.env import MockEnv
    from poetry.utils.env import VirtualEnv
    from tests.types import CommandTesterFactory
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("run")


@pytest.fixture(autouse=True)
def patches(mocker: MockerFixture, env: MockEnv) -> None:
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=env)


@pytest.fixture
def poetry_with_scripts(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Poetry:
    source = fixture_dir("scripts")

    return project_factory(
        name="scripts",
        pyproject_content=(source / "pyproject.toml").read_text(encoding="utf-8"),
        source=source,
    )


def test_run_passes_all_args(app_tester: ApplicationTester, env: MockEnv):
    app_tester.execute("run python -V")
    assert [["python", "-V"]] == env.executed


def test_run_keeps_options_passed_before_command(
    app_tester: ApplicationTester, env: MockEnv
):
    app_tester.execute("-V --no-ansi run python", decorated=True)

    assert not app_tester.io.is_decorated()
    assert app_tester.io.fetch_output() == app_tester.io.remove_format(
        app_tester.application.long_version + "\n"
    )
    assert [] == env.executed


def test_run_has_helpful_error_when_command_not_found(
    app_tester: ApplicationTester, env: MockEnv, capfd: pytest.CaptureFixture[str]
):
    env._execute = True
    app_tester.execute("run nonexistent-command")

    assert env.executed == [["nonexistent-command"]]
    assert app_tester.status_code == 1
    if WINDOWS:
        # On Windows we use a shell to run commands which provides its own error
        # message when a command is not found that is not captured by the
        # ApplicationTester but is captured by pytest, and we can access it via capfd.
        # The expected string in this assertion assumes Command Prompt (cmd.exe) is the
        # shell used.
        assert capfd.readouterr().err.splitlines() == [
            (
                "'nonexistent-command' is not recognized as an internal or external"
                " command,"
            ),
            "operable program or batch file.",
        ]
    else:
        assert app_tester.io.fetch_error() == "Command not found: nonexistent-command\n"


@pytest.mark.skipif(
    not WINDOWS,
    reason=(
        "Poetry only installs CMD script files for console scripts of editable"
        " dependencies on Windows"
    ),
)
def test_run_console_scripts_of_editable_dependencies_on_windows(
    tmp_venv: VirtualEnv,
    command_tester_factory: CommandTesterFactory,
):
    """
    On Windows, Poetry installs console scripts of editable dependencies by creating
    in the environment's `Scripts/` directory both:

        A) a Python file named after the console script (no `.py` extension) which
            imports and calls the console script using Python code
        B) a CMD script file also named after the console script
            (with `.cmd` extension) which calls `python.exe` to execute (A)

    This configuration enables calling the console script by name from `cmd.exe`
    because the `.cmd` file extension appears by default in the PATHEXT environment
    variable that `cmd.exe` uses to determine which file should be executed if a
    filename without an extension is executed as a command.

    This test validates that you can also run such a CMD script file via `poetry run`
    just by providing the script's name without the `.cmd` extension.
    """
    tester = command_tester_factory("run", environment=tmp_venv)

    cmd_script_file = tmp_venv._bin_dir / "quix.cmd"
    # `/b` ensures we only exit the script instead of any cmd.exe proc that called it
    cmd_script_file.write_text("exit /b 123")
    # We prove that the CMD script executed successfully by verifying the exit code
    # matches what we wrote in the script
    assert tester.execute("quix") == 123


def test_run_script_exit_code(
    poetry_with_scripts: Poetry,
    command_tester_factory: CommandTesterFactory,
    tmp_venv: VirtualEnv,
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "os.execvpe",
        lambda file, args, env: subprocess.call([file] + args[1:], env=env),
    )
    install_tester = command_tester_factory(
        "install",
        poetry=poetry_with_scripts,
        environment=tmp_venv,
    )
    assert install_tester.execute() == 0
    tester = command_tester_factory(
        "run", poetry=poetry_with_scripts, environment=tmp_venv
    )
    assert tester.execute("exit-code") == 42
    assert tester.execute("return-code") == 42
