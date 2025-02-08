from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.core.constraints.version import Version

from poetry.utils._compat import WINDOWS
from poetry.utils.env.python.providers import PoetryPythonPathProvider


if TYPE_CHECKING:
    from poetry.config.config import Config


def test_poetry_python_path_provider_no_pythons() -> None:
    provider = PoetryPythonPathProvider.create()
    assert provider
    assert not provider.paths


def test_poetry_python_path_provider(config: Config) -> None:
    config.python_installation_dir.mkdir()

    # CPython
    cpython_dir = config.python_installation_dir / "cpython@3.9.1"
    if not WINDOWS:
        cpython_dir /= "bin"
    cpython_dir.mkdir(parents=True)
    (cpython_dir / "python").touch()

    # PyPy
    pypy_dir = config.python_installation_dir / "pypy@3.10.8"
    if not WINDOWS:
        pypy_dir /= "bin"
    pypy_dir.mkdir(parents=True)
    (pypy_dir / "pypy").touch()

    provider = PoetryPythonPathProvider.create()

    assert provider

    assert provider.paths == [cpython_dir, pypy_dir]
    assert len(list(provider.find_pythons())) == 2

    assert provider.installation_bin_paths(Version.parse("3.9.1"), "cpython") == [
        cpython_dir
    ]
    assert provider.installation_bin_paths(Version.parse("3.9.2"), "cpython") == []
    assert provider.installation_bin_paths(Version.parse("3.10.8"), "pypy") == [
        pypy_dir
    ]
    assert provider.installation_bin_paths(Version.parse("3.10.8"), "cpython") == []
