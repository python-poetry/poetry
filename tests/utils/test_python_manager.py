from __future__ import annotations

import sys

from pathlib import Path

from poetry.core.constraints.version import Version

from poetry.utils.env.python_manager import Python


def test_python_get_version_on_the_fly() -> None:
    python = Python(executable=sys.executable)

    assert python.executable == Path(sys.executable)
    assert python.version == Version.parse(
        ".".join([str(s) for s in sys.version_info[:3]])
    )
    assert python.patch_version == Version.parse(
        ".".join([str(s) for s in sys.version_info[:3]])
    )
    assert python.minor_version == Version.parse(
        ".".join([str(s) for s in sys.version_info[:2]])
    )
