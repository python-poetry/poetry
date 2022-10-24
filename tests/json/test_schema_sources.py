from __future__ import annotations

from pathlib import Path

from poetry.factory import Factory
from poetry.toml import TOMLFile


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "source"


def test_pyproject_toml_valid_legacy() -> None:
    toml = TOMLFile(FIXTURE_DIR / "complete_valid_legacy.toml").read()
    content = toml["tool"]["poetry"]
    assert Factory.validate(content) == {"errors": [], "warnings": []}


def test_pyproject_toml_valid() -> None:
    toml = TOMLFile(FIXTURE_DIR / "complete_valid.toml").read()
    content = toml["tool"]["poetry"]
    assert Factory.validate(content) == {"errors": [], "warnings": []}


def test_pyproject_toml_invalid_url() -> None:
    toml = TOMLFile(FIXTURE_DIR / "complete_invalid_url.toml").read()
    content = toml["tool"]["poetry"]
    assert Factory.validate(content) == {
        "errors": ["[source.0] 'url' is a required property"],
        "warnings": [],
    }


def test_pyproject_toml_invalid_priority() -> None:
    toml = TOMLFile(FIXTURE_DIR / "complete_invalid_priority.toml").read()
    content = toml["tool"]["poetry"]
    assert Factory.validate(content) == {
        "errors": [
            "[source.0.priority] 'arbitrary' is not one of ['primary', 'default',"
            " 'secondary']"
        ],
        "warnings": [],
    }


def test_pyproject_toml_invalid_priority_legacy_and_new() -> None:
    toml = TOMLFile(
        FIXTURE_DIR / "complete_invalid_priority_legacy_and_new.toml"
    ).read()
    content = toml["tool"]["poetry"]
    assert Factory.validate(content) == {
        "errors": [
            "[source.0] {'name': 'pypi-simple', 'url': "
            "'https://pypi.org/simple/', 'default': False, 'priority': "
            "'primary'} should not be valid under {'anyOf': [{'required': "
            "['priority', 'default']}, {'required': ['priority', "
            "'secondary']}]}"
        ],
        "warnings": [],
    }
