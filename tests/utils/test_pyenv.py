import pytest

from poetry.utils.pyenv import PyEnv
from poetry.utils.pyenv import PyEnvNotFound


def test_pyenv_versions():
    pyenv = PyEnv()

    try:
        pyenv.load()
    except Exception as ex:
        assert isinstance(ex, PyEnvNotFound) is True
        assert bool(pyenv) is False
        return

    assert bool(pyenv) is True

    for version in pyenv.versions():
        assert pyenv.executable(version).exists()
