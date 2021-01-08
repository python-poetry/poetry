import os
import tempfile

import pytest

from poetry.utils._compat import WINDOWS
from poetry.utils._compat import Path


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
    not WINDOWS, reason="This test asserts Windows-specific compatibility",
)
def test_run_console_scripts_on_windows(tmp_venv, command_tester_factory, mocker):
    """Test that `poetry run` on Windows finds console scripts.

    On Windows, Poetry installs console scripts of editable
    dependencies by creating in the `Scripts/` directory both:

    1. The Bash script one expects on Linux (an extension-less file),
    with a shebang to launch Python, import the given module, and call
    the given function.

    2. A Batch script (with the `.cmd` file extension) which makes
    this Bash script work on Windows by calling Python directly and
    then executing the script from (1).

    This works because Windows programs (like the command prompt,
    PowerShell, "run" box, `start`, `where`, etc.) know to append
    extensions from the `PATHEXT` environment variable when looking
    for named programs. This is the Windows version of `chmod +x`.
    Sine Poetry is cross-platform, `poetry run` also needs to look for
    programs with this algorithm, and so this is a regression test.

    This test asserts that you can a console script via `poetry run`
    just by providing its name without the `.cmd` extension (the
    common use case).

    """
    new_environ = {}
    new_environ.update(os.environ)
    new_environ["PATHEXT"] = ".BAT;.CMD"  # ensure environ vars are deterministic
    mocker.patch("os.environ", new_environ)

    tester = command_tester_factory("run", environment=tmp_venv)
    bat_script = tmp_venv._bin_dir / "console_script.bat"
    cmd_script = tmp_venv._bin_dir / "console_script.cmd"

    cmd_script.write_text("exit 15")
    bat_script.write_text("exit 30")
    assert tester.execute("console_script") == 30
    assert tester.execute("console_script.bat") == 30
    assert tester.execute("console_script.cmd") == 15


@pytest.mark.skipif(
    not WINDOWS, reason="This test asserts Windows-specific compatibility",
)
def test_script_external_to_env(tmp_venv, command_tester_factory, mocker):
    """
    If a script exists on the path outside poetry, or in the current directory,
    poetry run should still work
    """
    new_environ = {}
    new_environ.update(os.environ)

    tester = command_tester_factory("run", environment=tmp_venv)

    # create directory and add it to the PATH
    with tempfile.TemporaryDirectory() as tmp_dir_name:
        # add script to current directory
        script_in_cur_dir = tempfile.NamedTemporaryFile(
            "w", dir=".", suffix=".CMD", delete=False
        )
        script_in_cur_dir.write("exit 30")
        script_in_cur_dir.close()

        try:
            # add script to the new directory
            script = Path(tmp_dir_name) / "console_script.cmd"
            script.write_text("exit 15")

            new_environ[
                "PATHEXT"
            ] = ".BAT;.CMD"  # ensure environ vars are deterministic
            new_environ["PATH"] = os.environ["PATH"] + os.pathsep + tmp_dir_name
            mocker.patch("os.environ", new_environ)

            # poetry run will find it as it searched the path
            assert tester.execute("console_script") == 15
            assert tester.execute(script_in_cur_dir.name) == 30

        finally:
            os.unlink(script_in_cur_dir.name)
