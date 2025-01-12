from __future__ import annotations

import sys

from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from poetry.utils.env import SystemEnv


if TYPE_CHECKING:
    from packaging.tags import Tag


class NullEnv(SystemEnv):
    def __init__(
        self, path: Path | None = None, base: Path | None = None, execute: bool = False
    ) -> None:
        if path is None:
            path = Path(sys.prefix)

        super().__init__(path, base=base)

        self._execute = execute
        self.executed: list[list[str]] = []

    @cached_property
    def paths(self) -> dict[str, str]:
        paths = self.get_paths()
        paths["platlib"] = str(self._path / "platlib")
        paths["purelib"] = str(self._path / "purelib")
        paths["scripts"] = str(self._path / "scripts")
        paths["data"] = str(self._path / "data")
        return paths

    def _run(self, cmd: list[str], **kwargs: Any) -> str:
        self.executed.append(cmd)

        if self._execute:
            return super()._run(cmd, **kwargs)
        return ""

    def execute(self, bin: str, *args: str, **kwargs: Any) -> int:
        self.executed.append([bin, *list(args)])

        if self._execute:
            return super().execute(bin, *args, **kwargs)
        return 0

    def _bin(self, bin: str) -> str:
        return bin


class MockEnv(NullEnv):
    def __init__(
        self,
        version_info: tuple[int, int, int] = (3, 7, 0),
        *,
        python_implementation: str = "CPython",
        platform: str = "darwin",
        platform_machine: str = "amd64",
        os_name: str = "posix",
        is_venv: bool = False,
        sys_path: list[str] | None = None,
        marker_env: dict[str, Any] | None = None,
        supported_tags: list[Tag] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        self._version_info = version_info
        self._python_implementation = python_implementation
        self._platform = platform
        self._platform_machine = platform_machine
        self._os_name = os_name
        self._is_venv = is_venv
        self._sys_path = sys_path
        self._mock_marker_env = marker_env
        self._supported_tags = supported_tags

    @property
    def platform(self) -> str:
        return self._platform

    @property
    def platform_machine(self) -> str:
        return self._platform_machine

    @property
    def os(self) -> str:
        return self._os_name

    @property
    def sys_path(self) -> list[str]:
        if self._sys_path is None:
            return super().sys_path

        return self._sys_path

    def get_marker_env(self) -> dict[str, Any]:
        if self._mock_marker_env is not None:
            return self._mock_marker_env

        marker_env = super().get_marker_env()
        marker_env["python_implementation"] = self._python_implementation
        marker_env["version_info"] = self._version_info
        marker_env["python_version"] = ".".join(str(v) for v in self._version_info[:2])
        marker_env["python_full_version"] = ".".join(str(v) for v in self._version_info)
        marker_env["sys_platform"] = self._platform
        marker_env["platform_machine"] = self._platform_machine
        marker_env["interpreter_name"] = self._python_implementation.lower()
        marker_env["interpreter_version"] = "cp" + "".join(
            str(v) for v in self._version_info[:2]
        )

        return marker_env

    def is_venv(self) -> bool:
        return self._is_venv
