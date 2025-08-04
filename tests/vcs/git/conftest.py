from __future__ import annotations

from typing import TYPE_CHECKING

import dulwich.repo
import pytest

from tests.vcs.git.git_fixture import TempRepoFixture


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def temp_repo(tmp_path: Path) -> TempRepoFixture:
    """Temporary repository with 2 commits"""
    repo = dulwich.repo.Repo.init(str(tmp_path))
    worktree = repo.get_worktree()

    # init commit
    (tmp_path / "foo").write_text("foo", encoding="utf-8")
    worktree.stage(["foo"])

    init_commit = worktree.commit(
        committer=b"User <user@example.com>",
        author=b"User <user@example.com>",
        message=b"init",
        no_verify=True,
    )

    # one commit which is not "head"
    (tmp_path / "bar").write_text("bar", encoding="utf-8")
    worktree.stage(["bar"])
    middle_commit = worktree.commit(
        committer=b"User <user@example.com>",
        author=b"User <user@example.com>",
        message=b"extra",
        no_verify=True,
    )

    # extra commit
    (tmp_path / "third").write_text("third file", encoding="utf-8")
    worktree.stage(["third"])

    head_commit = worktree.commit(
        committer=b"User <user@example.com>",
        author=b"User <user@example.com>",
        message=b"extra",
        no_verify=True,
    )

    return TempRepoFixture(
        path=tmp_path,
        repo=repo,
        init_commit=init_commit.decode(),
        middle_commit=middle_commit.decode(),
        head_commit=head_commit.decode(),
    )
