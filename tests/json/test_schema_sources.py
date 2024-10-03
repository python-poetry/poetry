from __future__ import annotations

from pathlib import Path
from typing import Any

from poetry.factory import Factory
from poetry.toml import TOMLFile


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "source"


def test_pyproject_toml_valid() -> None:
    toml: dict[str, Any] = TOMLFile(FIXTURE_DIR / "complete_valid.toml").read()
    assert Factory.validate(toml) == {"errors": [], "warnings": []}


def test_pyproject_toml_invalid_priority() -> None:
    toml: dict[str, Any] = TOMLFile(
        FIXTURE_DIR / "complete_invalid_priority.toml"
    ).read()
    assert Factory.validate(toml) == {
        "errors": [
            "data.source[0].priority must be one of ['primary',"
            " 'supplemental', 'explicit']"
        ],
        "warnings": [],
    }
