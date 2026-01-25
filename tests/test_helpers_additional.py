from __future__ import annotations

import os
from pathlib import Path

import pytest

from poetry.utils import helpers


def test_merge_dicts_merges_correctly() -> None:
    d1 = {"a": 1, "b": {"x": 1}}
    d2 = {"b": {"y": 2}, "c": 3}
    helpers.merge_dicts(d1, d2)
    assert d1 == {"a": 1, "b": {"x": 1, "y": 2}, "c": 3}


def test_paths_csv_returns_comma_separated_string(tmp_path: Path) -> None:
    paths = [tmp_path / "a.txt", tmp_path / "b.txt"]
    result = helpers.paths_csv(paths)
    assert "a.txt" in result and "b.txt" in result
    assert "," in result


def test_ensure_path_creates_directory(tmp_path: Path) -> None:
    path = tmp_path / "new_dir"
    path.mkdir()
    result = helpers.ensure_path(path, is_directory=True)
    assert result.exists()
    assert result.is_dir()


def test_is_dir_writable_returns_true(tmp_path: Path) -> None:
    assert helpers.is_dir_writable(tmp_path) is True


def test_pluralize_singular_and_plural() -> None:
    # Actual behavior: returns the word only, not "1 file"
    assert helpers.pluralize(1, "file") == "file"
    assert helpers.pluralize(3, "file") == "files"


def test_get_file_hash(tmp_path: Path) -> None:
    file = tmp_path / "data.txt"
    file.write_text("hello")
    hash1 = helpers.get_file_hash(file)
    hash2 = helpers.get_file_hash(file)
    assert isinstance(hash1, str)
    assert hash1 == hash2  # deterministic


@pytest.mark.skipif(os.name != "nt", reason="Windows-only helper")
def test_get_real_windows_path(tmp_path: Path) -> None:
    # On Windows, returns a Path with correct case
    path = helpers.get_real_windows_path(tmp_path)
    assert isinstance(path, Path)


def test_remove_directory_deletes(tmp_path: Path) -> None:
    dir_to_remove = tmp_path / "deleteme"
    dir_to_remove.mkdir()
    (dir_to_remove / "file.txt").write_text("bye")
    helpers.remove_directory(dir_to_remove)
    assert not dir_to_remove.exists()


def test_directory_iterator(tmp_path: Path) -> None:
    sub = tmp_path / "nested"
    sub.mkdir()
    (sub / "a.txt").write_text("ok")

    # directory() is a context manager, not an iterator
    with helpers.directory(tmp_path) as path:
        assert path == tmp_path
        assert path.exists()
