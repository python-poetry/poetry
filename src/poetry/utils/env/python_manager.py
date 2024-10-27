from __future__ import annotations

import shutil
import subprocess
import sys

from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from cleo.io.null_io import NullIO
from cleo.io.outputs.output import Verbosity
from poetry.core.constraints.version import Version
from poetry.core.constraints.version import parse_constraint

from poetry.utils._compat import decode
from poetry.utils.env.exceptions import NoCompatiblePythonVersionFoundError
from poetry.utils.env.script_strings import GET_PYTHON_VERSION_ONELINER


if TYPE_CHECKING:
    from cleo.io.io import IO

    from poetry.config.config import Config
    from poetry.poetry import Poetry


class Python:
    def __init__(self, executable: str | Path, version: Version | None = None) -> None:
        self.executable = Path(executable)
        self._version = version

    @property
    def version(self) -> Version:
        if not self._version:
            if self.executable == Path(sys.executable):
                python_version = ".".join(str(v) for v in sys.version_info[:3])
            else:
                encoding = "locale" if sys.version_info >= (3, 10) else None
                python_version = decode(
                    subprocess.check_output(
                        [str(self.executable), "-c", GET_PYTHON_VERSION_ONELINER],
                        text=True,
                        encoding=encoding,
                    ).strip()
                )
            self._version = Version.parse(python_version)

        return self._version

    @cached_property
    def patch_version(self) -> Version:
        return Version.from_parts(
            major=self.version.major,
            minor=self.version.minor,
            patch=self.version.patch,
        )

    @cached_property
    def minor_version(self) -> Version:
        return Version.from_parts(major=self.version.major, minor=self.version.minor)

    @staticmethod
    def _full_python_path(python: str) -> Path | None:
        # eg first find pythonXY.bat on windows.
        path_python = shutil.which(python)
        if path_python is None:
            return None

        try:
            encoding = "locale" if sys.version_info >= (3, 10) else None
            executable = subprocess.check_output(
                [path_python, "-c", "import sys; print(sys.executable)"],
                text=True,
                encoding=encoding,
            ).strip()
            return Path(executable)

        except subprocess.CalledProcessError:
            return None

    @staticmethod
    def _detect_active_python(io: IO) -> Path | None:
        io.write_error_line(
            "Trying to detect current active python executable as specified in"
            " the config.",
            verbosity=Verbosity.VERBOSE,
        )

        executable = Python._full_python_path("python")

        if executable is not None:
            io.write_error_line(f"Found: {executable}", verbosity=Verbosity.VERBOSE)
        else:
            io.write_error_line(
                "Unable to detect the current active python executable. Falling"
                " back to default.",
                verbosity=Verbosity.VERBOSE,
            )

        return executable

    @classmethod
    def get_system_python(cls) -> Python:
        return cls(executable=sys.executable)

    @classmethod
    def get_by_name(cls, python_name: str) -> Python | None:
        executable = cls._full_python_path(python_name)
        if not executable:
            return None

        return cls(executable=executable)

    @classmethod
    def get_preferred_python(cls, config: Config, io: IO | None = None) -> Python:
        io = io or NullIO()

        if not config.get("virtualenvs.use-poetry-python") and (
            active_python := Python._detect_active_python(io)
        ):
            return cls(executable=active_python)

        return cls.get_system_python()

    @classmethod
    def get_compatible_python(cls, poetry: Poetry, io: IO | None = None) -> Python:
        io = io or NullIO()
        supported_python = poetry.package.python_constraint
        python = None

        for suffix in [
            *sorted(
                poetry.package.AVAILABLE_PYTHONS,
                key=lambda v: (v.startswith("3"), -len(v), v),
                reverse=True,
            ),
            "",
        ]:
            if len(suffix) == 1:
                if not parse_constraint(f"^{suffix}.0").allows_any(supported_python):
                    continue
            elif suffix and not supported_python.allows_any(
                parse_constraint(suffix + ".*")
            ):
                continue

            python_name = f"python{suffix}"
            if io.is_debug():
                io.write_error_line(f"<debug>Trying {python_name}</debug>")

            executable = cls._full_python_path(python_name)
            if executable is None:
                continue

            candidate = cls(executable)
            if supported_python.allows(candidate.patch_version):
                python = candidate
                io.write_error_line(
                    f"Using <c1>{python_name}</c1> ({python.patch_version})"
                )
                break

        if not python:
            raise NoCompatiblePythonVersionFoundError(poetry.package.python_versions)

        return python
