from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.toml import TOMLFile


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def pyproject_toml(tmp_path: Path) -> Path:
    path = tmp_path / "pyproject.toml"
    with path.open(mode="w", encoding="utf-8"):
        pass
    return path


@pytest.fixture
def build_system_section(pyproject_toml: Path) -> str:
    content = """
[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
"""
    with pyproject_toml.open(mode="a", encoding="utf-8") as f:
        f.write(content)
    return content


@pytest.fixture
def poetry_section(pyproject_toml: Path) -> str:
    content = """
[tool.poetry]
name = "poetry"

[tool.poetry.dependencies]
python = "^3.5"
"""
    with pyproject_toml.open(mode="a", encoding="utf-8") as f:
        f.write(content)
    return content


@pytest.fixture
def exclude_newer_section(pyproject_toml: Path, poetry_section: str) -> str:
    # Read the current content and insert exclude-newer before [tool.poetry.dependencies]
    content = TOMLFile(pyproject_toml).read()
    # Insert exclude-newer at the [tool.poetry] level
    content["tool"]["poetry"]["exclude-newer"] = "1 week"  # type: ignore[index]
    TOMLFile(pyproject_toml).write(content)
    return 'exclude-newer = "1 week"'
