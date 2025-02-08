from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.core.constraints.version import Version

from poetry.utils.env.python.providers import PoetryPythonPathProvider


if TYPE_CHECKING:
    from pathlib import Path


def test_poetry_python_path_provider_no_pythons() -> None:
    provider = PoetryPythonPathProvider.create()
    assert provider
    assert not provider.paths


def test_poetry_python_path_provider(poetry_managed_pythons: list[Path]) -> None:
    provider = PoetryPythonPathProvider.create()

    assert provider

    assert provider.paths == poetry_managed_pythons
    assert len(list(provider.find_pythons())) == 2

    assert provider.installation_bin_paths(Version.parse("3.9.1"), "cpython") == [
        p for p in poetry_managed_pythons if "cpython" in p.name and "3.9.1" in p.name
    ]
    assert provider.installation_bin_paths(Version.parse("3.9.2"), "cpython") == []
    assert provider.installation_bin_paths(Version.parse("3.10.8"), "pypy") == [
        p for p in poetry_managed_pythons if "pypy" in p.name and "3.10.8" in p.name
    ]
    assert provider.installation_bin_paths(Version.parse("3.10.8"), "cpython") == []
