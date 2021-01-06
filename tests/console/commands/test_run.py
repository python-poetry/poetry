import os

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
    not WINDOWS, reason="This test asserts Windows-specific compatibility",
)
def test_run_console_scripts_on_windows(tmp_venv, command_tester_factory):
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
    path_ext_start = os.environ["PATHEXT"]
    try:
        os.environ["PATHEXT"] = ".BAT;.CMD"  # ensure environ vars are deterministic
        tester = command_tester_factory("run", environment=tmp_venv)
        bat_script = tmp_venv._bin_dir / "console_script.bat"
        cmd_script = tmp_venv._bin_dir / "console_script.cmd"

        cmd_script.write_text("exit 15")
        bat_script.write_text("exit 30")
        assert tester.execute("console_script") == 30
        assert tester.execute("console_script.bat") == 30
        assert tester.execute("console_script.cmd") == 15
    finally:
        os.environ["PATHEXT"] = path_ext_start
