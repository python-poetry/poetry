from __future__ import annotations

import sys

from pathlib import Path

import pytest

from poetry.utils._compat import is_relative_to


@pytest.mark.parametrize(
    ("path1", "path2", "expected"),
    [
        ("a", "a", True),
        ("a/b", "a/b", True),
        ("a/b", "a", True),
        ("a", "a/b", False),
        ("a/b/c/d", "a/b", True),
        ("a/b", "a/b/c/d", False),
    ],
)
def test_is_relative_to(path1: str, path2: str, expected: bool) -> None:
    assert is_relative_to(Path(path1), Path(path2)) is expected


@pytest.mark.parametrize(
    ("path1", "path2", "expected"),
    [
        ("/", "/", True),
        ("/a/b", "/a/b", True),
        ("/a/b", "/a", True),
        ("/a", "/a/b", False),
        ("/a/b/c/d", "/a/b", True),
        ("/a/b", "/a/b/c/d", False),
    ],
)
@pytest.mark.skipif(sys.platform == "win32", reason="non-Windows paths")
def test_is_relative_to_non_win32(path1: str, path2: str, expected: bool) -> None:
    assert is_relative_to(Path(path1), Path(path2)) is expected


@pytest.mark.parametrize(
    ("path1", "path2", "expected"),
    [
        ("C:\\", "C:\\", True),
        (r"C:\a\b", r"C:\a\b", True),
        (r"C:\a\b", r"C:\a", True),
        (r"C:\a", r"C:\a\b", False),
        (r"C:\a\b\c\d", r"C:\a\b", True),
        (r"C:\a\b", r"C:\a\b\c\d", False),
        (r"C:\a\b", r"D:\a", False),
        (r"C:\a\b", "D:\\", False),
        (r"\\server\a\b", r"\\server\a", True),
        (r"\\server\a", r"\\server\a\b", False),
        (r"\\server2\a\b", r"\\server\a", False),
        # long path prefix
        (r"\\?\C:\a\b", r"\\?\C:\a", True),
        (r"\\?\C:\a\b", r"C:\a", True),
        (r"C:\a\b", r"\\?\C:\a", True),
        (r"\\?\C:\a", r"\\?\C:\a\b", False),
        # long path UNC prefix
        (r"\\?\UNC\server\a\b", r"\\?\UNC\server\a", True),
        (r"\\?\UNC\server\a\b", r"\\server\a", True),
        (r"\\server\a\b", r"\\?\UNC\server\a", True),
        (r"\\?\UNC\server\a", r"\\?\UNC\server\a\b", False),
    ],
)
@pytest.mark.skipif(sys.platform != "win32", reason="Windows paths")
def test_is_relative_to_win32(path1: str, path2: str, expected: bool) -> None:
    assert is_relative_to(Path(path1), Path(path2)) is expected
