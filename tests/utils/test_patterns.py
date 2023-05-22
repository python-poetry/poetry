from __future__ import annotations

import pytest

from poetry.utils import patterns


@pytest.mark.parametrize(
    ["filename", "expected"],
    [
        (
            "markdown_captions-2-py3-none-any.whl",
            {
                "namever": "markdown_captions-2",
                "name": "markdown_captions",
                "ver": "2",
                "build": None,
                "pyver": "py3",
                "abi": "none",
                "plat": "any",
            },
        ),
        (
            "SQLAlchemy-1.3.20-cp27-cp27mu-manylinux2010_x86_64.whl",
            {
                "namever": "SQLAlchemy-1.3.20",
                "name": "SQLAlchemy",
                "ver": "1.3.20",
                "build": None,
                "pyver": "cp27",
                "abi": "cp27mu",
                "plat": "manylinux2010_x86_64",
            },
        ),
    ],
)
def test_wheel_file_re(filename: str, expected: dict[str, str | None]) -> None:
    match = patterns.wheel_file_re.match(filename)
    assert match is not None
    groups = match.groupdict()

    assert groups == expected
