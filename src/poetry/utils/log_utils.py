from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from poetry.core.packages.package import Package

    from poetry.utils.env import Env


def format_build_wheel_log(package: Package, env: Env) -> str:
    """Format a log message indicating
    that a wheel is being built for the given package and environment."""
    marker_env = env.marker_env

    python_version_info = marker_env.get(
        "version_info", ("<unknown>", "<unknown>", "<unknown>")
    )
    python_version = (
        f"{python_version_info[0]}.{python_version_info[1]}.{python_version_info[2]}"
    )
    platform = marker_env.get("sys_platform", "<unknown-platform>")
    architecture = marker_env.get("platform_machine", "<unknown-arch>")

    message = (
        f" <info>Building a wheel file for {package.pretty_name} "
        f"for Python {python_version} on {platform}-{architecture}</info>"
    )
    return message
