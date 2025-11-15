from __future__ import annotations

import sys

from typing import TYPE_CHECKING

from poetry.core.constraints.version import Version

from poetry.utils.env.python.providers import PoetryPythonPathProvider
from poetry.utils.env.python.providers import ShutilWhichPythonProvider


if TYPE_CHECKING:
    from tests.types import MockedPoetryPythonRegister


def test_shutil_which_python_provider() -> None:
    provider = ShutilWhichPythonProvider.create()
    assert provider
    pythons = list(provider.find_pythons())
    assert len(pythons) == 1
    assert pythons[0].minor == sys.version_info.minor


def test_poetry_python_path_provider_no_pythons() -> None:
    provider = PoetryPythonPathProvider.create()
    assert provider
    assert not provider.paths


def test_poetry_python_path_provider(
    mocked_poetry_managed_python_register: MockedPoetryPythonRegister,
) -> None:
    cpython_path = mocked_poetry_managed_python_register("3.9.1", "cpython")
    pypy_path = mocked_poetry_managed_python_register("3.10.8", "pypy")
    free_threaded_path = mocked_poetry_managed_python_register(
        "3.13.2", "cpython", free_threaded=True, with_install_dir=True
    )

    provider = PoetryPythonPathProvider.create()

    assert provider

    assert set(provider.paths) == {cpython_path, pypy_path, free_threaded_path}
    assert len(list(provider.find_pythons())) == 4

    assert provider.installation_bin_paths(Version.parse("3.9.1"), "cpython") == [
        cpython_path
    ]
    assert provider.installation_bin_paths(Version.parse("3.9.2"), "cpython") == []
    assert provider.installation_bin_paths(Version.parse("3.10.8"), "pypy") == [
        pypy_path
    ]
    assert provider.installation_bin_paths(Version.parse("3.10.8"), "cpython") == []
    assert provider.installation_bin_paths(
        Version.parse("3.13.2"), "cpython", free_threaded=True
    ) == [free_threaded_path]
