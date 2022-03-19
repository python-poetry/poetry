from __future__ import annotations

import shutil

from pathlib import Path
from typing import TYPE_CHECKING

import pytest


try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

if TYPE_CHECKING:
    from poetry.core.vcs import Git
    from pytest_mock import MockerFixture


def mock_clone(self: Git, source: str, dest: Path) -> None:
    # Checking source to determine which folder we need to copy
    parts = urlparse.urlparse(source)

    folder = (
        Path(__file__).parent.parent
        / "fixtures"
        / "git"
        / parts.netloc
        / parts.path.lstrip("/").rstrip(".git")
    )

    shutil.rmtree(str(dest))
    shutil.copytree(str(folder), str(dest))


@pytest.fixture(autouse=True)
def setup(mocker: MockerFixture) -> None:
    # Patch git module to not actually clone projects
    mocker.patch("poetry.core.vcs.git.Git.clone", new=mock_clone)
    mocker.patch("poetry.core.vcs.git.Git.checkout", new=lambda *_: None)
    p = mocker.patch("poetry.core.vcs.git.Git.rev_parse")
    p.return_value = "9cf87a285a2d3fbb0b9fa621997b3acc3631ed24"
