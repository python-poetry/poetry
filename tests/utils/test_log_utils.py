from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from poetry.utils.log_utils import format_build_wheel_log


if TYPE_CHECKING:
    from poetry.core.packages.package import Package

    from poetry.utils.env import Env


class DummyEnv:
    @property
    def marker_env(self) -> dict[str, object]:
        return {
            "version_info": (3, 13, 1),
            "sys_platform": "win32",
            "platform_machine": "AMD64",
        }


class DummyPackage:
    pretty_name = "demo"
    full_pretty_version = "1.2.3"


def test_format_build_wheel_log() -> None:
    env = cast("Env", DummyEnv())
    package = cast("Package", DummyPackage())
    result = format_build_wheel_log(package, env)
    expected = (
        " <info>Building a wheel file for demo "
        "(no prebuilt wheel available for Python 3.13.1 on win32-AMD64)</info>"
    )
    assert result == expected
