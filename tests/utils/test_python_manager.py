from __future__ import annotations

import os
import sys
import textwrap

from pathlib import Path
from typing import TYPE_CHECKING

import findpython
import packaging.version
import pytest

from poetry.core.constraints.version import Version

from poetry.utils.env.python import Python


if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

    from poetry.config.config import Config
    from tests.types import MockedPythonRegister
    from tests.types import ProjectFactory


def test_python_get_version_on_the_fly() -> None:
    python = Python.get_system_python()

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

    assert python.executable.resolve() == findpython.find().executable.resolve()
    assert python.version == Version.parse(
        ".".join(str(v) for v in sys.version_info[:3])
    )


def test_python_get_preferred_default(config: Config) -> None:
    python = Python.get_preferred_python(config)

    version_info: tuple[int, int, int] | tuple[int, int, int, str, int]
    if sys.version_info[3] == "final":
        version_info = sys.version_info[:3]
    elif sys.version_info[3] == "candidate":
        version_info = (*sys.version_info[:3], "rc", sys.version_info[4])
    else:
        version_info = sys.version_info[:5]

    assert python.executable.resolve() == Path(sys.executable).resolve()
    assert python.version == Version.parse(".".join(str(v) for v in version_info))


def test_get_preferred_python_use_poetry_python_disabled(
    config: Config, mocker: MockerFixture
) -> None:
    mocker.patch(
        "poetry.utils.env.python.Python.get_active_python",
        return_value=Python(
            python=findpython.PythonVersion(
                executable=Path("/usr/bin/python3.7"),
                _version=packaging.version.Version("3.7.1"),
                _interpreter=Path("/usr/bin/python3.7"),
            )
        ),
    )

    config.config["virtualenvs"]["use-poetry-python"] = False
    python = Python.get_preferred_python(config)

    assert python.executable.as_posix().startswith("/usr/bin/python")
    assert python.version == Version.parse("3.7.1")


def test_get_preferred_python_use_poetry_python_disabled_fallback(
    config: Config, with_no_active_python: MagicMock
) -> None:
    config.config["virtualenvs"]["use-poetry-python"] = False
    python = Python.get_preferred_python(config)

    assert with_no_active_python.call_count == 1
    assert python.executable.resolve() == Path(sys.executable).resolve()


def test_fallback_on_detect_active_python(with_no_active_python: MagicMock) -> None:
    active_python = Python.get_active_python()
    assert active_python is None
    assert with_no_active_python.call_count == 1


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_detect_active_python_with_bat(
    tmp_path: Path, without_mocked_findpython: None
) -> None:
    """On Windows pyenv uses batch files for python management."""
    python_wrapper = tmp_path / "python.bat"

    encoding = "locale" if sys.version_info >= (3, 10) else None
    with python_wrapper.open("w", encoding=encoding) as f:
        f.write(
            textwrap.dedent(f"""
            @echo off
            SET PYTHON_EXE="{sys.executable}"
            %PYTHON_EXE% %*
        """)
        )
    os.environ["PATH"] = str(python_wrapper.parent) + os.pathsep + os.environ["PATH"]

    python = Python.get_active_python()
    assert python is not None

    # TODO: Asses if Poetry needs to discover real path in these cases as
    # this is not a symlink and won't be handled by findpython
    assert python.executable.as_posix() == Path(sys.executable).as_posix()
    assert python.version == Version.parse(
        ".".join(str(v) for v in sys.version_info[:3])
    )


def test_python_find_compatible(
    project_factory: ProjectFactory, mocked_python_register: MockedPythonRegister
) -> None:
    # Note: This test may fail on Windows systems using Python from the Microsoft Store,
    # as the executable is named `py.exe`, which is not currently recognized by
    # Python.get_compatible_python. This issue will be resolved in #2117.
    # However, this does not cause problems in our case because Poetry's own
    # Python interpreter is used before attempting to find another compatible version.
    fixture = Path(__file__).parent.parent / "fixtures" / "simple_project"
    poetry = project_factory("simple-project", source=fixture)
    mocked_python_register("3.12")
    python = Python.get_compatible_python(poetry)

    assert Version.from_parts(3, 4) <= python.version <= Version.from_parts(4, 0)
