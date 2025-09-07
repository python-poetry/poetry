from __future__ import annotations

import shutil

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from dulwich.repo import Repo

from poetry.console.exceptions import PoetryRuntimeError
from poetry.vcs.git.backend import Git
from poetry.vcs.git.backend import annotated_tag
from poetry.vcs.git.backend import is_revision_sha
from poetry.vcs.git.backend import urlpathjoin


if TYPE_CHECKING:
    from pathlib import Path

    from tests.vcs.git.git_fixture import TempRepoFixture


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
    "url, expected_result",
    [
        ("ssh://git@github.com/org/repo", "ssh://git@github.com/other-repo"),
        ("ssh://git@github.com/org/repo/", "ssh://git@github.com/org/other-repo"),
    ],
)
def test_urlpathjoin(url: str, expected_result: str) -> None:
    path = "../other-repo"
    result = urlpathjoin(url, path)
    assert result == expected_result


@pytest.mark.skip_git_mock
def test_clone_success(tmp_path: Path, temp_repo: TempRepoFixture) -> None:
    source_root_dir = tmp_path / "test-repo"
    Git.clone(
        url=temp_repo.path.as_uri(), source_root=source_root_dir, name="clone-test"
    )

    target_dir = source_root_dir / "clone-test"
    assert (target_dir / ".git").is_dir()


@pytest.mark.skip_git_mock
def test_short_sha_not_in_head(tmp_path: Path, temp_repo: TempRepoFixture) -> None:
    source_root_dir = tmp_path / "test-repo"
    Git.clone(
        url=temp_repo.path.as_uri(),
        revision=temp_repo.middle_commit[:6],
        name="clone-test",
        source_root=source_root_dir,
    )

    target_dir = source_root_dir / "clone-test"
    assert (target_dir / ".git").is_dir()


@pytest.mark.skip_git_mock
def test_clone_existing_locked_tag(tmp_path: Path, temp_repo: TempRepoFixture) -> None:
    source_root_dir = tmp_path / "test-repo"
    source_url = temp_repo.path.as_uri()
    Git.clone(url=source_url, source_root=source_root_dir, name="clone-test")

    tag_ref = source_root_dir / "clone-test" / ".git" / "refs" / "tags" / "v1"
    assert tag_ref.is_file()

    tag_ref_lock = tag_ref.with_name("v1.lock")
    shutil.copy(tag_ref, tag_ref_lock)

    with pytest.raises(PoetryRuntimeError) as exc_info:
        Git.clone(url=source_url, source_root=source_root_dir, name="clone-test")

    expected_short = (
        f"Failed to clone {source_url} at 'refs/heads/master',"
        f" unable to acquire file lock for {tag_ref}."
    )
    assert str(exc_info.value) == expected_short
    assert exc_info.value.get_text(debug=True, strip=True) == (
        f"{expected_short}\n\n"
        "Note: This error arises from interacting with the specified vcs source"
        " and is likely not a Poetry issue.\n"
        "This issue could be caused by any of the following;\n\n"
        "- another process is holding the file lock\n"
        "- another process crashed while holding the file lock\n\n"
        f"Try again later or remove the {tag_ref_lock} manually"
        " if you are sure no other process is holding it."
    )
