import pytest

from poetry.utils._compat import WINDOWS


@pytest.fixture
def tester(command_tester_factory):
    return command_tester_factory("run")


@pytest.fixture(autouse=True)
def patches(mocker, env):
    mocker.patch("poetry.utils.env.EnvManager.get", return_value=env)


def test_run_passes_all_args(tester, env):
    tester.execute("python -V")
    assert [["python", "-V"]] == env.executed


@pytest.mark.skipif(
    not WINDOWS,
    reason="Poetry only installs CMD script files for console scripts of editable dependencies on Windows",
)
def test_run_console_scripts_of_editable_dependencies_on_windows(
    tmp_venv, command_tester_factory, monkeypatch
):
    """
    On Windows, Poetry installs console scripts of editable dependencies by creating in the environment's `Scripts/`
    directory both:

        A) a Python file named after the console script (no `.py` extension) which imports and calls the console script
            using Python code
        B) a CMD script file also named after the console script (with `.cmd` extension) which calls `python.exe` to
            execute (A)

    This configuration enables calling the console script by name from `cmd.exe` because the `.cmd` file extension
    appears by default in the PATHEXT environment variable that `cmd.exe` uses to determine which file should be
    executed if a filename without an extension is executed as a command.

    This test validates that you can also run such a CMD script file via `poetry run` just by providing the script's
    name without the `.cmd` extension.
    """
    tester = command_tester_factory("run", environment=tmp_venv)

    cmd_script_file = tmp_venv._bin_dir / "quix.cmd"
    # `/b` ensures we only exit the script instead of any cmd.exe process that called it
    cmd_script_file.write_text("exit /b 123")
    # We prove that the CMD script executed successfully by verifying the exit code matches what we wrote in the script
    assert tester.execute("quix") == 123
