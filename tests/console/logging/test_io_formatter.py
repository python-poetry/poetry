from __future__ import annotations

from logging import LogRecord
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.console.logging.io_formatter import IOFormatter
from poetry.console.logging.io_formatter import _log_prefix
from poetry.console.logging.io_formatter import _path_to_package


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    ("record_name", "record_pathname", "record_msg", "expected"),
    [
        ("poetry", "foo/bar.py", "msg", "msg"),
        ("poetry.core", "foo/bar.py", "msg", "msg"),
        ("baz", "syspath/foo/bar.py", "msg", "[foo:baz] msg"),
        ("root", "syspath/foo/bar.py", "1\n\n2", "[foo] 1\n[foo] \n[foo] 2"),
    ],
)
def test_format(
    mocker: MockerFixture,
    record_name: str,
    record_pathname: str,
    record_msg: str,
    expected: str,
) -> None:
    mocker.patch("sys.path", [str(Path("syspath"))])
    record = LogRecord(record_name, 0, record_pathname, 0, record_msg, (), None)
    formatter = IOFormatter()
    assert formatter.format(record) == expected


@pytest.mark.parametrize(
    ("record_name", "record_pathname", "expected"),
    [
        ("root", "syspath/foo/bar.py", "foo"),
        ("baz", "syspath/foo/bar.py", "foo:baz"),
        ("baz", "unexpected/foo/bar.py", "bar:baz"),
    ],
)
def test_log_prefix(
    mocker: MockerFixture,
    record_name: str,
    record_pathname: str,
    expected: str,
) -> None:
    mocker.patch("sys.path", [str(Path("syspath"))])
    record = LogRecord(record_name, 0, record_pathname, 0, "msg", (), None)
    assert _log_prefix(record) == expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("python-l/lib/python3.9/site-packages/foo/bar/baz.py", "foo"),  # Linux
        ("python-w/lib/site-packages/foo/bar/baz.py", "foo"),  # Windows
        ("unexpected/foo/bar/baz.py", None),  # unexpected
    ],
)
def test_path_to_package(
    mocker: MockerFixture, path: str, expected: str | None
) -> None:
    mocker.patch(
        "sys.path",
        # We just put the Linux and the Windows variants in the path,
        # so we do not have to create different mocks based on the subtest.
        [
            # On Linux, only the site-packages directory is in the path.
            str(Path("python-l/lib/python3.9/site-packages")),
            # On Windows, both the base directory and the site-packages directory
            # are in the path.
            str(Path("python-w")),
            str(Path("python-w/other")),  # this one is just to test for robustness
            str(Path("python-w/lib/site-packages")),
            str(Path("python-w/lib")),  # this one is just to test for robustness
        ],
    )
    assert _path_to_package(Path(path)) == expected
