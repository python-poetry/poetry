from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from poetry.poetry import Poetry
    from poetry.utils.env import EnvManager


@pytest.fixture
def venv_name(
    manager: EnvManager,
    poetry: Poetry,
) -> str:
    return manager.generate_env_name(
        poetry.package.name,
        str(poetry.file.parent),
    )
