from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cleo.io.buffered_io import BufferedIO

from poetry.utils.env import EnvManager


if TYPE_CHECKING:
    from poetry.poetry import Poetry
    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture
def poetry(project_factory: ProjectFactory, fixture_dir: FixtureDirGetter) -> Poetry:
    return project_factory("simple", source=fixture_dir("simple_project"))


@pytest.fixture
def io() -> BufferedIO:
    return BufferedIO()


@pytest.fixture
def manager(poetry: Poetry, io: BufferedIO) -> EnvManager:
    return EnvManager(poetry, io)
