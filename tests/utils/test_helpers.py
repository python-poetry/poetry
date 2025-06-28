from __future__ import annotations

import base64
import re
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from poetry.core.utils.helpers import parse_requires
from requests.exceptions import ChunkedEncodingError

from poetry.utils.helpers import (
    Downloader,
    HTTPRangeRequestSupportedError,
    download_file,
    ensure_path,
    get_file_hash,
    get_highest_priority_hash_type,
    is_dir_writable,
    pluralize,
)

if TYPE_CHECKING:
    from httpretty import httpretty
    from httpretty.core import HTTPrettyRequest

    from tests.conftest import Config
    from tests.types import FixtureDirGetter


# --- Tests for pluralize ---
def test_pluralize() -> None:
    assert pluralize(1, "apple") == "apple"
    assert pluralize(0, "apple") == "apples"
    assert pluralize(2, "apple") == "apples"
    assert pluralize(3, "") == "s"


# --- Tests for parse_requires ---
def test_parse_requires() -> None:
    requires = """\
jsonschema>=2.6.0.0,<3.0.0.0
lockfile>=0.12.0.0,<0.13.0.0
pip-tools>=1.11.0.0,<2.0.0.0
pkginfo>=1.4.0.0,<2.0.0.0
pyrsistent>=0.14.2.0,<0.15.0.0
toml>=0.9.0.0,<0.10.0.0
cleo>=0.6.0.0,<0.7.0.0
cachy>=0.1.1.0,<0.2.0.0
cachecontrol>=0.12.4.0,<0.13.0.0
requests>=2.18.0.0,<3.0.0.0
msgpack-python>=0.5.0.0,<0.6.0.0
pyparsing>=2.2.0.0,<3.0.0.0
requests-toolbelt>=0.8.0.0,<0.9.0.0

[:(python_version >= \"2.7.0.0\" and python_version < \"2.8.0.0\")\
 or (python_version >= \"3.4.0.0\" and python_version < \"3.5.0.0\")]
typing>=3.6.0.0,<4.0.0.0

[:python_version >= \"2.7.0.0\" and python_version < \"2.8.0.0\"]
virtualenv>=15.2.0.0,<16.0.0.0
pathlib2>=2.3.0.0,<3.0.0.0

[:python_version >= \"3.4.0.0\" and python_version < \"3.6.0.0\"]
zipfile36>=0.1.0.0,<0.2.0.0

[dev]
isort@ git+git://github.com/timothycrosley/isort.git@e63ae06ec7d70b06df9e528357650281a3d3ec22#egg=isort
"""
    result = parse_requires(requires)
    expected = [
        "jsonschema>=2.6.0.0,<3.0.0.0",
        "lockfile>=0.12.0.0,<0.13.0.0",
        "pip-tools>=1.11.0.0,<2.0.0.0",
        "pkginfo>=1.4.0.0,<2.0.0.0",
        "pyrsistent>=0.14.2.0,<0.15.0.0",
        "toml>=0.9.0.0,<0.10.0.0",
        "cleo>=0.6.0.0,<0.7.0.0",
        "cachy>=0.1.1.0,<0.2.0.0",
        "cachecontrol>=0.12.4.0,<0.13.0.0",
        "requests>=2.18.0.0,<3.0.0.0",
        "msgpack-python>=0.5.0.0,<0.6.0.0",
        "pyparsing>=2.2.0.0,<3.0.0.0",
        "requests-toolbelt>=0.8.0.0,<0.9.0.0",
        'typing>=3.6.0.0,<4.0.0.0 ; (python_version >= "2.7.0.0" and python_version < "2.8.0.0") or (python_version >= "3.4.0.0" and python_version < "3.5.0.0")',
        'virtualenv>=15.2.0.0,<16.0.0.0 ; python_version >= "2.7.0.0" and python_version < "2.8.0.0"',
        'pathlib2>=2.3.0.0,<3.0.0.0 ; python_version >= "2.7.0.0" and python_version < "2.8.0.0"',
        'zipfile36>=0.1.0.0,<0.2.0.0 ; python_version >= "3.4.0.0" and python_version < "3.6.0.0"',
        'isort@ git+git://github.com/timothycrosley/isort.git@e63ae06ec7d70b06df9e528357650281a3d3ec22#egg=isort ; extra == "dev"',
    ]
    assert result == expected


# --- Tests for is_dir_writable ---
def test_is_dir_writable_returns_true_for_writable_dir(tmp_path: Path) -> None:
    assert is_dir_writable(tmp_path) is True


@pytest.mark.parametrize("create_flag", [False, True])
def test_is_dir_writable_creates_dir_if_missing(tmp_path: Path, create_flag: bool) -> None:
    missing = tmp_path / "missing"
    expected = create_flag
    assert is_dir_writable(missing, create=create_flag) is expected
    assert missing.exists() is expected


def test_is_dir_writable_returns_false_if_unwritable_posix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    if sys.platform.startswith("win"):
        pytest.skip("chmod 0o555 is unreliable on Windows")

    tmp_path.chmod(0o555)
    try:
        assert is_dir_writable(tmp_path) is False
    finally:
        tmp_path.chmod(0o755)


def test_is_dir_writable_simulates_unwritable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    called = {"yes": False}

    def boom(*_, **__):
        called["yes"] = True
        raise OSError("fake write fail")

    monkeypatch.setattr(tempfile, "TemporaryFile", boom)
    assert is_dir_writable(tmp_path) is False
    assert called["yes"]
