from __future__ import annotations

from pathlib import Path
from typing import Any

from poetry.factory import Factory
from poetry.toml import TOMLFile


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "source"


def test_pyproject_toml_valid_legacy() -> None:
    toml: dict[str, Any] = TOMLFile(FIXTURE_DIR / "complete_valid_legacy.toml").read()
    content = toml["tool"]["poetry"]
    assert Factory.validate(content) == {"errors": [], "warnings": []}


def test_pyproject_toml_valid() -> None:
    toml: dict[str, Any] = TOMLFile(FIXTURE_DIR / "complete_valid.toml").read()
    content = toml["tool"]["poetry"]
    assert Factory.validate(content) == {"errors": [], "warnings": []}


def test_pyproject_toml_invalid_priority() -> None:
    toml: dict[str, Any] = TOMLFile(
        FIXTURE_DIR / "complete_invalid_priority.toml"
    ).read()
    content = toml["tool"]["poetry"]
    assert Factory.validate(content) == {
        "errors": [
            "data.source[0].priority must be one of ['primary', 'default', "
            "'secondary', 'supplemental', 'explicit']"
        ],
        "warnings": [],
    }


def test_pyproject_toml_invalid_priority_legacy_and_new() -> None:
    toml: dict[str, Any] = TOMLFile(
        FIXTURE_DIR / "complete_invalid_priority_legacy_and_new.toml"
    ).read()
    content = toml["tool"]["poetry"]
    assert Factory.validate(content) == {
        "errors": ["data.source[0] must NOT match a disallowed definition"],
        "warnings": [],
    }
