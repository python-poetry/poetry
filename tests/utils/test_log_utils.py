from __future__ import annotations

from poetry.core.packages.package import Package

from poetry.utils.env.mock_env import MockEnv
from poetry.utils.log_utils import format_build_wheel_log


def test_format_build_wheel_log() -> None:
    env = MockEnv(version_info=(3, 13, 1), platform="win32", platform_machine="AMD64")
    package = Package(name="demo", version="1.2.3")
    result = format_build_wheel_log(package, env)
    expected = (
        " <info>Building a wheel file for demo for Python 3.13.1 on win32-AMD64</info>"
    )
    assert result == expected
