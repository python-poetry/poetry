from __future__ import annotations

import os
import subprocess
import sys

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from cleo.io.null_io import NullIO
from poetry.core.constraints.version import Version

from poetry.utils.env.python_manager import Python
from tests.utils.env.test_env_manager import check_output_wrapper


if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from poetry.config.config import Config


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


def test_python_get_system_python() -> None:
    python = Python.get_system_python()

    assert python.executable == Path(sys.executable)
    assert python.version == Version.parse(
        ".".join(str(v) for v in sys.version_info[:3])
    )


def test_python_get_preferred_default(config: Config) -> None:
    python = Python.get_preferred_python(config)

    assert python.executable == Path(sys.executable)
    assert python.version == Version.parse(
        ".".join(str(v) for v in sys.version_info[:3])
    )


def test_python_get_preferred_activated(config: Config, mocker: MockerFixture) -> None:
    mocker.patch(
        "subprocess.check_output",
        side_effect=check_output_wrapper(Version.parse("3.7.1")),
    )
    config.config["virtualenvs"]["prefer-active-python"] = True
    python = Python.get_preferred_python(config)

    assert python.executable.as_posix().startswith("/usr/bin/python")
    assert python.version == Version.parse("3.7.1")


def test_python_get_preferred_activated_fallback(
    config: Config, mocker: MockerFixture
) -> None:
    config.config["virtualenvs"]["prefer-active-python"] = True
    with mocker.patch(
        "subprocess.check_output",
        side_effect=subprocess.CalledProcessError(1, "some command"),
    ):
        python = Python.get_preferred_python(config)

    assert python.executable == Path(sys.executable)


def test_fallback_on_detect_active_python(mocker: MockerFixture) -> None:
    m = mocker.patch(
        "subprocess.check_output",
        side_effect=subprocess.CalledProcessError(1, "some command"),
    )

    active_python = Python._detect_active_python(NullIO())

    assert active_python is None
    assert m.call_count == 1


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_detect_active_python_with_bat(tmp_path: Path) -> None:
    """On Windows pyenv uses batch files for python management."""
    python_wrapper = tmp_path / "python.bat"
    wrapped_python = Path(r"C:\SpecialPython\python.exe")
    encoding = "locale" if sys.version_info >= (3, 10) else None
    with python_wrapper.open("w", encoding=encoding) as f:
        f.write(f"@echo {wrapped_python}")
    os.environ["PATH"] = str(python_wrapper.parent) + os.pathsep + os.environ["PATH"]

    active_python = Python._detect_active_python(NullIO())

    assert active_python == wrapped_python
