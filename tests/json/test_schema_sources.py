from __future__ import annotations

from pathlib import Path

from poetry.core.toml import TOMLFile

from poetry.factory import Factory


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "source"


def test_pyproject_toml_valid() -> None:
    toml = TOMLFile(FIXTURE_DIR / "complete_valid.toml").read()
    content = toml["tool"]["poetry"]
    assert Factory.validate(content) == {"errors": [], "warnings": []}


def test_pyproject_toml_invalid() -> None:
    toml = TOMLFile(FIXTURE_DIR / "complete_invalid.toml").read()
    content = toml["tool"]["poetry"]
    assert Factory.validate(content) == {
        "errors": ["[source.0] 'url' is a required property"],
        "warnings": [],
    }
