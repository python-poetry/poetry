from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from poetry.utils.env.null_env import NullEnv


if TYPE_CHECKING:
    from packaging.tags import Tag

    from poetry.utils.env.base_env import MarkerEnv
    from poetry.utils.env.base_env import PythonVersion


class MockEnv(NullEnv):
    def __init__(
        self,
        version_info: tuple[int, int, int] | PythonVersion = (3, 7, 0),
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

        if len(version_info) == 3:
            version_info = (*version_info, "final", 0)
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

    def get_marker_env(self) -> MarkerEnv:
        marker_env = super().get_marker_env()
        marker_env["version_info"] = self._version_info
        marker_env["python_version"] = ".".join(str(v) for v in self._version_info[:2])
        marker_env["python_full_version"] = ".".join(
            str(v) for v in self._version_info[:3]
        )
        marker_env["sys_platform"] = self._platform
        marker_env["platform_machine"] = self._platform_machine
        marker_env["interpreter_name"] = self._python_implementation.lower()
        marker_env["interpreter_version"] = "cp" + "".join(
            str(v) for v in self._version_info[:2]
        )

        if self._mock_marker_env is not None:
            for key, value in self._mock_marker_env.items():
                marker_env[key] = value  # type: ignore[literal-required]

        return marker_env

    def is_venv(self) -> bool:
        return self._is_venv
