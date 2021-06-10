from pathlib import Path

from poetry.core.semver.version import Version
from poetry.utils.pyenv import Pyenv


def test_pyenv_loaded(mocker):
    mocker.patch(
        "poetry.utils.pyenv.Pyenv._locate_command",
        side_effect=lambda: Path("pyenv"),
    )

    def check_output(cmd: str, *args, **kwargs):
        if "versions" in cmd:
            return "3.6.9\n3.9.5\n3.10.0\n"
        return "/prefix"

    mocker.patch("subprocess.check_output", side_effect=check_output)
    pyenv = Pyenv()
    pyenv.load()
    assert bool(pyenv) is True

    for version in pyenv.versions():
        sv = Version.parse(version)
        python_bin = "python{}.{}".format(sv.major, sv.minor)
        assert pyenv.executable(version).as_posix() == "/prefix/bin/" + python_bin


def test_pyenv_not_loaded(mocker):
    mocker.patch(
        "poetry.utils.pyenv.Pyenv._locate_command",
        side_effect=lambda: None,
    )
    pyenv = Pyenv()
    pyenv.load()
    assert bool(pyenv) is False
