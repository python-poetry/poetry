import pytest

from poetry.utils.pyenv import Pyenv
from poetry.utils.pyenv import PyenvNotFound


def test_pyenv_versions():
    pyenv = Pyenv()

    try:
        pyenv.load()
    except Exception as ex:
        assert isinstance(ex, PyenvNotFound) is True
        assert bool(pyenv) is False
        return

    assert bool(pyenv) is True

    for version in pyenv.versions():
        assert pyenv.executable(version).exists()
