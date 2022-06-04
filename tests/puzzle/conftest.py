from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.helpers import mock_clone


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def setup(mocker: MockerFixture) -> None:
    # Patch git module to not actually clone projects
    mocker.patch("poetry.vcs.git.Git.clone", new=mock_clone)
    p = mocker.patch("poetry.vcs.git.Git.get_revision")
    p.return_value = "9cf87a285a2d3fbb0b9fa621997b3acc3631ed24"
