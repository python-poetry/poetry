import pytest

from poetry.utils.pyenv import Pyenv


def test_pyenv_versions():
    pyenv = Pyenv()

    try:
        pyenv.load()
    except Exception:
        assert bool(pyenv) is False
        return

    if bool(pyenv) is True:
        for version in pyenv.versions():
            assert pyenv.executable(version).exists()
