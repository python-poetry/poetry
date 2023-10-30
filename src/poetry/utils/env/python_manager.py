from __future__ import annotations

import subprocess
import sys

from functools import cached_property
from pathlib import Path

from poetry.core.constraints.version import Version

from poetry.utils._compat import decode
from poetry.utils.env.script_strings import GET_PYTHON_VERSION_ONELINER


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
