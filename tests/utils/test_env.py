import os

from poetry.utils._compat import Path
from poetry.utils.env import Env
from poetry.utils.env import VirtualEnv

from pytest import skip
from re import sub


def test_virtualenvs_with_spaces_in_their_path_work_as_expected(tmp_dir):
    venv_path = Path(tmp_dir) / "Virtual Env"

    Env.build_venv(str(venv_path))

    venv = VirtualEnv(venv_path)

    assert venv.run("python", "-V", shell=True).startswith("Python")


def test_env_get_in_project_venv(tmp_dir, environ):
    if "VIRTUAL_ENV" in environ:
        del environ["VIRTUAL_ENV"]

    (Path(tmp_dir) / ".venv").mkdir()

    venv = Env.get(cwd=Path(tmp_dir))

    assert venv.path == Path(tmp_dir) / ".venv"


def test_virtualenvs_pip_and_setuptools_versions(tmp_dir):
    from pip import __version__ as pip_version
    from setuptools import __version__ as setuptools_version

    if pip_version == "10.0.1" and setuptools_version == "39.0.1":
        skip(
            "System 'pip' and 'setuptools' are default versions from 'ensurepip'."
            "Will not detect if they do not get updated after 'venv' creation."
        )

    venv_path = Path(tmp_dir) / "CheckPipSetuptools"

    Env.build_venv(str(venv_path))

    venv = VirtualEnv(venv_path)

    from pip import __version__ as pip_version

    venv_pip_version = venv.run(
        "python", "-c", '"from __future__ import print_function;from pip import __version__; print(__version__)"',
        shell=True
    )
    venv_pip_version = sub(r'\s', '', venv_pip_version)

    venv_setuptools_version = venv.run(
        "python", "-c", '"from __future__ import print_function;from setuptools import __version__; print(__version__)"',
        shell=True
    )
    venv_setuptools_version = sub(r'\s', '', venv_setuptools_version)

    assert venv_pip_version == pip_version and venv_setuptools_version == setuptools_version