import pytest

from poetry.utils.pyenv import Pyenv


def test_pyenv_versions():
    pyenv = Pyenv.load()
    print(pyenv.versions())

    print(pyenv.python_path("3.7.10"))
