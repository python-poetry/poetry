from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.helpers import MOCK_DEFAULT_GIT_REVISION
from tests.helpers import mock_clone


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def setup(mocker: MockerFixture) -> None:
    # Patch git module to not actually clone projects
    mocker.patch("poetry.vcs.git.Git.clone", new=mock_clone)
    p = mocker.patch("poetry.vcs.git.Git.get_revision")
    p.return_value = MOCK_DEFAULT_GIT_REVISION
