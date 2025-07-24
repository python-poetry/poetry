from __future__ import annotations

import json

from importlib.resources import files
from pathlib import Path
from typing import Any

from poetry.factory import Factory
from poetry.toml import TOMLFile


SCHEMA_FILE = files("poetry.json") / "schemas" / "poetry.json"
FIXTURE_DIR = Path(__file__).parent / "fixtures"
SOURCE_FIXTURE_DIR = FIXTURE_DIR / "source"


def test_pyproject_toml_valid() -> None:
    toml: dict[str, Any] = TOMLFile(SOURCE_FIXTURE_DIR / "complete_valid.toml").read()
    assert Factory.validate(toml) == {"errors": [], "warnings": []}


def test_pyproject_toml_invalid_priority() -> None:
    toml: dict[str, Any] = TOMLFile(
        SOURCE_FIXTURE_DIR / "complete_invalid_priority.toml"
    ).read()
    assert Factory.validate(toml) == {
        "errors": [
            "tool.poetry.source[0].priority must be one of ['primary',"
            " 'supplemental', 'explicit']"
        ],
        "warnings": [],
    }


def test_self_valid() -> None:
    toml: dict[str, Any] = TOMLFile(FIXTURE_DIR / "self_valid.toml").read()
    assert Factory.validate(toml) == {"errors": [], "warnings": []}


def test_self_invalid_version() -> None:
    toml: dict[str, Any] = TOMLFile(FIXTURE_DIR / "self_invalid_version.toml").read()
    assert Factory.validate(toml) == {
        "errors": ["tool.poetry.requires-poetry must be string"],
        "warnings": [],
    }


def test_self_invalid_plugin() -> None:
    toml: dict[str, Any] = TOMLFile(FIXTURE_DIR / "self_invalid_plugin.toml").read()
    assert Factory.validate(toml) == {
        "errors": [
            "tool.poetry.requires-plugins.foo must be valid exactly by one definition"
            " (0 matches found)"
        ],
        "warnings": [],
    }


def test_dependencies_is_consistent_to_poetry_core_schema() -> None:
    with SCHEMA_FILE.open(encoding="utf-8") as f:
        schema = json.load(f)
    dependency_definitions = {
        key: value for key, value in schema["definitions"].items() if "depend" in key
    }
    with (files("poetry.core") / "json" / "schemas" / "poetry-schema.json").open(
        encoding="utf-8"
    ) as f:
        core_schema = json.load(f)
    core_dependency_definitions = {
        key: value
        for key, value in core_schema["definitions"].items()
        if "depend" in key
    }
    assert dependency_definitions == core_dependency_definitions
