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


@pytest.fixture
def poetry_with_file_scripts(
    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter
) -> Poetry:
    source = fixture_dir("file_scripts_project")

    return project_factory(
        name="file-scripts-project",
        pyproject_content=(source / "pyproject.toml").read_text(encoding="utf-8"),
        source=source,
    )


def test_run_passes_all_args(app_tester: ApplicationTester, env: MockEnv) -> None:
    app_tester.execute("run python -V")
    assert env.executed == [["python", "-V"]]


def test_run_is_not_eager(app_tester: ApplicationTester, env: MockEnv) -> None:
    app_tester.execute("--no-ansi -C run -install", decorated=True)
    assert (
        app_tester.io.fetch_error().strip()
        == "Specified path 'run' is not a valid directory."
    )
    assert env.executed == []


def test_run_passes_args_after_run_before_command(
    app_tester: ApplicationTester, env: MockEnv
) -> None:
    app_tester.execute("run -P. python -V", decorated=True)
    assert env.executed == [["python", "-V"]]


@pytest.mark.parametrize(
    "args",
    [
        "-vP run run",
        "run -vP run",
        "-vPrun run",
        "run -vPrun ",
        "-v --project=run run",
        "-v run --project=run",
        "-v --directory=run run",
        "run -v --directory=run",
    ],
)
def test_run_passes_args_after_run_before_command_name_conflict(
    args: str,
    app_tester: ApplicationTester,
    env: MockEnv,
    project_factory: ProjectFactory,
) -> None:
    poetry = project_factory("run")
    path = poetry.file.path.parent
    path.rename(path.parent / "run")

    app_tester.execute(f"{args} python -V", decorated=True)
    assert (
        app_tester.io.remove_format(app_tester.io.fetch_error())
        == f"Using virtualenv: {env.path}\n"
    )
    assert env.executed == [["python", "-V"]]


def test_run_keeps_options_passed_before_command_args_combined_short_opts(
    app_tester: ApplicationTester, env: MockEnv
) -> None:
    app_tester.execute("run -VP. --no-ansi python", decorated=True)

    assert not app_tester.io.is_decorated()
    assert app_tester.io.fetch_output() == app_tester.io.remove_format(
        app_tester.application.long_version + "\n"
    )
    assert env.executed == []


def test_run_keeps_options_passed_before_command_args(
    app_tester: ApplicationTester, env: MockEnv
) -> None:
    app_tester.execute("run -V --no-ansi python", decorated=True)

    assert not app_tester.io.is_decorated()
    assert app_tester.io.fetch_output() == app_tester.io.remove_format(
        app_tester.application.long_version + "\n"
    )
    assert env.executed == []


def test_run_keeps_options_passed_before_command(
    app_tester: ApplicationTester, env: MockEnv
) -> None:
    app_tester.execute("-V --no-ansi run python", decorated=True)

    assert not app_tester.io.is_decorated()
    assert app_tester.io.fetch_output() == app_tester.io.remove_format(
        app_tester.application.long_version + "\n"
    )
    assert env.executed == []


def test_run_has_helpful_error_when_command_not_found(
    app_tester: ApplicationTester, env: MockEnv, capfd: pytest.CaptureFixture[str]
) -> None:
    nonexistent_command = "nonexistent-command"
    env._execute = True
    app_tester.execute(f"run {nonexistent_command}")

    assert env.executed == [[nonexistent_command]]
    assert app_tester.status_code == 1
    if WINDOWS:
        # On Windows we use a shell to run commands which provides its own error
        # message when a command is not found that is not captured by the
        # ApplicationTester but is captured by pytest, and we can access it via capfd.
        # The exact error message depends on the system language. Thus, we check only
        # for the name of the command.
        assert nonexistent_command in capfd.readouterr().err
    else:
        assert (
            app_tester.io.fetch_error() == f"Command not found: {nonexistent_command}\n"
        )


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
) -> None:
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
    cmd_script_file.write_text("exit /b 123", encoding="locale")
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
        lambda file, args, env: subprocess.call([file, *args[1:]], env=env),
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


@pytest.mark.parametrize(
    "installed_script", [False, True], ids=["not installed", "installed"]
)
def test_run_script_sys_argv0(
    installed_script: bool,
    poetry_with_scripts: Poetry,
    command_tester_factory: CommandTesterFactory,
    tmp_venv: VirtualEnv,
    mocker: MockerFixture,
) -> None:
    """
    If RunCommand calls an installed script defined in pyproject.toml,
    sys.argv[0] must be set to the full path of the script.
    """
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=tmp_venv)
    mocker.patch(
        "os.execvpe",
        lambda file, args, env: subprocess.call([file, *args[1:]], env=env),
    )

    install_tester = command_tester_factory(
        "install",
        poetry=poetry_with_scripts,
        environment=tmp_venv,
    )
    assert install_tester.execute() == 0
    if not installed_script:
        for path in tmp_venv.script_dirs[0].glob("check-argv0*"):
            path.unlink()

    tester = command_tester_factory(
        "run", poetry=poetry_with_scripts, environment=tmp_venv
    )
    argv1 = "absolute" if installed_script else "relative"
    assert tester.execute(f"check-argv0 {argv1}") == 0

    if installed_script:
        expected_message = ""
    else:
        expected_message = """\
Warning: 'check-argv0' is an entry point defined in pyproject.toml, but it's not \
installed as a script. You may get improper `sys.argv[0]`.

The support to run uninstalled scripts will be removed in a future release.

Run `poetry install` to resolve and get rid of this message.

"""
    assert tester.io.fetch_error() == expected_message


def test_run_file_script_from_reference_when_not_installed(
    poetry_with_file_scripts: Poetry,
    command_tester_factory: CommandTesterFactory,
    env: MockEnv,
) -> None:
    tester = command_tester_factory("run", poetry=poetry_with_file_scripts)

    assert tester.execute("my-script arg1 arg2") == 0

    reference = poetry_with_file_scripts.file.path.parent / "bin" / "my-script.sh"
    assert env.executed == [[str(reference), "arg1", "arg2"]]
    assert "not installed as a script" in tester.io.fetch_error()


def test_run_file_script_from_the_environment(
    poetry_with_file_scripts: Poetry,
    command_tester_factory: CommandTesterFactory,
    env: MockEnv,
) -> None:
    script_dir = env.script_dirs[0]
    script_dir.mkdir(parents=True, exist_ok=True)
    installed_script = script_dir / f"my-script{'.cmd' if WINDOWS else ''}"
    installed_script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    tester = command_tester_factory("run", poetry=poetry_with_file_scripts)

    assert tester.execute("my-script") == 0
    assert env.executed == [[str(installed_script)]]
    assert tester.io.fetch_error() == ""


def test_run_file_script_with_missing_reference(
    project_factory: ProjectFactory,
    fixture_dir: FixtureDirGetter,
    command_tester_factory: CommandTesterFactory,
    env: MockEnv,
) -> None:
    source = fixture_dir("file_scripts_missing_ref_project")
    poetry = project_factory(
        name="missing-file-script",
        pyproject_content=(source / "pyproject.toml").read_text(encoding="utf-8"),
        source=source,
    )

    tester = command_tester_factory("run", poetry=poetry)

    assert tester.execute("missing-script") == 1
    assert "Command not found: missing-script" in tester.io.fetch_error()
    assert env.executed == []


def test_run_console_script_defined_as_table(
    project_factory: ProjectFactory,
    fixture_dir: FixtureDirGetter,
    command_tester_factory: CommandTesterFactory,
    env: MockEnv,
) -> None:
    source = fixture_dir("file_scripts_project")
    content = (
        (source / "pyproject.toml")
        .read_text(encoding="utf-8")
        .replace(
            'console-entry = "file_scripts_project:main"',
            'console-entry = { reference = "file_scripts_project:main",'
            ' type = "console" }',
        )
    )
    poetry = project_factory(
        name="file-scripts-project-console-table",
        pyproject_content=content,
        source=source,
    )

    tester = command_tester_factory("run", poetry=poetry)

    assert tester.execute("console-entry") == 0
    (executed,) = env.executed
    assert executed[0] == "python"
    assert "import_module('file_scripts_project')" in executed[2]


@pytest.mark.skipif(WINDOWS, reason="The file script fixture uses a bash shebang.")
def test_run_file_script_uses_the_installed_file(
    poetry_with_file_scripts: Poetry,
    command_tester_factory: CommandTesterFactory,
    tmp_venv: VirtualEnv,
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "os.execvpe",
        lambda file, args, env: subprocess.call([file, *args[1:]], env=env),
    )
    install_tester = command_tester_factory(
        "install", poetry=poetry_with_file_scripts, environment=tmp_venv
    )
    assert install_tester.execute() == 0

    installed_script = tmp_venv.script_dirs[0] / "my-script"
    assert installed_script.exists()
    installed_script.write_text("#!/bin/sh\nexit 42\n", encoding="utf-8")
    installed_script.chmod(0o755)

    tester = command_tester_factory(
        "run", poetry=poetry_with_file_scripts, environment=tmp_venv
    )
    assert tester.execute("my-script") == 42
    assert tester.io.fetch_error() == ""
