from __future__ import annotations

import os

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from poetry.core.constraints.version import Version


if TYPE_CHECKING:
    from collections.abc import Callable

VERSION_3_7_1 = Version.parse("3.7.1")


def build_venv(path: Path | str, **_: Any) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def check_output_wrapper(
    version: Version = VERSION_3_7_1,
) -> Callable[[list[str], Any, Any], str]:
    def check_output(cmd: list[str], *args: Any, **kwargs: Any) -> str:
        # cmd is a list, like ["python", "-c", "do stuff"]
        python_cmd = cmd[-1]
        if "print(json.dumps(env))" in python_cmd:
            return (
                f'{{"version_info": [{version.major}, {version.minor},'
                f" {version.patch}]}}"
            )

        if "sys.version_info[:3]" in python_cmd:
            return version.text

        if "sys.version_info[:2]" in python_cmd:
            return f"{version.major}.{version.minor}"

        if "import sys; print(sys.executable)" in python_cmd:
            executable = cmd[0]
            basename = os.path.basename(executable)
            return f"/usr/bin/{basename}"

        if "print(sys.base_prefix)" in python_cmd:
            return "/usr"

        assert "import sys; print(sys.prefix)" in python_cmd
        return "/prefix"

    return check_output
