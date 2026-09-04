from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tomlkit.toml_document import TOMLDocument

from poetry.toml import TOMLError
from poetry.toml import TOMLFile


if TYPE_CHECKING:
    from pathlib import Path


def test_path_returns_the_given_path(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"

    assert TOMLFile(path).path == path


def test_exists_is_false_when_file_is_missing(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"

    assert TOMLFile(path).exists() is False


def test_exists_is_true_when_file_is_present(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"
    path.write_text("", encoding="utf-8")

    assert TOMLFile(path).exists() is True


def test_read_returns_a_toml_document(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"
    path.write_text('[tool.poetry]\nname = "poetry"\n', encoding="utf-8")

    content = TOMLFile(path).read()

    assert isinstance(content, TOMLDocument)
    assert content["tool"]["poetry"]["name"] == "poetry"


def test_read_raises_toml_error_on_invalid_toml(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"
    path.write_text("<<<<<<<<<<<", encoding="utf-8")

    with pytest.raises(TOMLError) as excval:
        TOMLFile(path).read()

    assert f"Invalid TOML file {path.as_posix()}" in str(excval.value)


def test_str_returns_posix_path(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"

    assert str(TOMLFile(path)) == path.as_posix()
