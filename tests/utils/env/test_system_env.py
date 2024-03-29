from __future__ import annotations

import sys

from pathlib import Path
from typing import TYPE_CHECKING

from poetry.utils.env import SystemEnv


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_get_marker_env_untagged_cpython(mocker: MockerFixture) -> None:
    mocker.patch("platform.python_version", return_value="3.11.9+")
    env = SystemEnv(Path(sys.prefix))
    marker_env = env.get_marker_env()
    assert marker_env["python_full_version"] == "3.11.9"
