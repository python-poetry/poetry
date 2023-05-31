from __future__ import annotations

import uuid

from typing import TYPE_CHECKING

from poetry.pyproject.toml import PyProjectTOML


if TYPE_CHECKING:
    from pathlib import Path


def test_pyproject_toml_reload(pyproject_toml: Path, poetry_section: str) -> None:
    pyproject = PyProjectTOML(pyproject_toml)
    name_original = pyproject.poetry_config["name"]
    name_new = str(uuid.uuid4())

    pyproject.poetry_config["name"] = name_new
    assert isinstance(pyproject.poetry_config["name"], str)
    assert pyproject.poetry_config["name"] == name_new

    pyproject.reload()
    assert pyproject.poetry_config["name"] == name_original


def test_pyproject_toml_save(
    pyproject_toml: Path, poetry_section: str, build_system_section: str
) -> None:
    pyproject = PyProjectTOML(pyproject_toml)

    name = str(uuid.uuid4())
    build_backend = str(uuid.uuid4())
    build_requires = str(uuid.uuid4())

    pyproject.poetry_config["name"] = name
    pyproject.build_system.build_backend = build_backend
    pyproject.build_system.requires.append(build_requires)

    pyproject.save()

    pyproject = PyProjectTOML(pyproject_toml)

    assert isinstance(pyproject.poetry_config["name"], str)
    assert pyproject.poetry_config["name"] == name
    assert pyproject.build_system.build_backend == build_backend
    assert build_requires in pyproject.build_system.requires
