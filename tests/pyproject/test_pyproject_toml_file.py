from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from poetry.core.exceptions import PoetryCoreError

from poetry.toml import TOMLFile


if TYPE_CHECKING:
    from pathlib import Path


def test_pyproject_toml_file_invalid(pyproject_toml: Path) -> None:
    with pyproject_toml.open(mode="a", encoding="utf-8") as f:
        f.write("<<<<<<<<<<<")

    with pytest.raises(PoetryCoreError) as excval:
        _ = TOMLFile(pyproject_toml).read()

    assert f"Invalid TOML file {pyproject_toml.as_posix()}" in str(excval.value)
