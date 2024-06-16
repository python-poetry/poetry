from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dulwich.repo import Repo

from poetry.vcs.git.backend import Git
from poetry.vcs.git.backend import annotated_tag
from poetry.vcs.git.backend import is_revision_sha
from poetry.vcs.git.backend import urlpathjoin


VALID_SHA = "c5c7624ef64f34d9f50c3b7e8118f7f652fddbbd"


def test_invalid_revision_sha() -> None:
    result = is_revision_sha("invalid_input")
    assert result is False


def test_valid_revision_sha() -> None:
    result = is_revision_sha(VALID_SHA)
    assert result is True


def test_invalid_revision_sha_min_len() -> None:
    result = is_revision_sha("c5c7")
    assert result is False


def test_invalid_revision_sha_max_len() -> None:
    result = is_revision_sha(VALID_SHA + "42")
    assert result is False


@pytest.mark.parametrize(
    ("url"),
    [
        "git@github.com:python-poetry/poetry.git",
        "https://github.com/python-poetry/poetry.git",
        "https://github.com/python-poetry/poetry",
        "https://github.com/python-poetry/poetry/",
    ],
)
def test_get_name_from_source_url(url: str) -> None:
    name = Git.get_name_from_source_url(url)
    assert name == "poetry"


@pytest.mark.parametrize(("tag"), ["my-tag", b"my-tag"])
def test_annotated_tag(tag: str | bytes) -> None:
    tag = annotated_tag("my-tag")
    assert tag == b"my-tag^{}"


def test_get_remote_url() -> None:
    repo = MagicMock(spec=Repo)
    repo.get_config.return_value.get.return_value = (
        b"https://github.com/python-poetry/poetry.git"
    )

    assert Git.get_remote_url(repo) == "https://github.com/python-poetry/poetry.git"


@pytest.mark.parametrize(
    ("url"), ["ssh://git@github.com/org/repo", "ssh://git@github.com/org/repo"]
)
def test_urlpathjoin(url: str) -> None:
    base = url
    path = "../other-repo"
    result = urlpathjoin(base, path)

    assert result == "ssh://git@github.com/other-repo"
