from __future__ import annotations

import re
import shutil
import subprocess
import typing

import dulwich.repo
import pytest

from poetry.vcs.git.system import SystemGit


if typing.TYPE_CHECKING:
    from pathlib import Path


GIT_NOT_INSTALLLED = shutil.which("git") is None


def get_head_sha(cwd: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        text=True,
    ).strip()


class TempRepoFixture(typing.NamedTuple):
    path: Path
    repo: dulwich.repo.Repo
    init_commit: str
    head_commit: str


@pytest.fixture()
def temp_repo(tmp_path: Path) -> TempRepoFixture:
    """Temporary repository with 2 commits"""
    repo = dulwich.repo.Repo.init(str(tmp_path))

    # init commit
    (tmp_path / "foo").write_text("foo")
    repo.stage(["foo"])

    init_commit = repo.do_commit(
        committer=b"User <user@example.com>",
        author=b"User <user@example.com>",
        message=b"init",
        no_verify=True,
    )

    # extra commit
    (tmp_path / "foo").write_text("bar")
    repo.stage(["foo"])

    head_commit = repo.do_commit(
        committer=b"User <user@example.com>",
        author=b"User <user@example.com>",
        message=b"extra",
        no_verify=True,
    )

    return TempRepoFixture(
        path=tmp_path,
        repo=repo,
        init_commit=init_commit.decode(),
        head_commit=head_commit.decode(),
    )


@pytest.mark.skipif(GIT_NOT_INSTALLLED, reason="These tests requires git cli")
class TestSystemGit:
    def test_clone_success(self, tmp_path: Path, temp_repo: TempRepoFixture) -> None:
        target_dir = tmp_path / "test-repo"
        SystemGit.clone(temp_repo.path.as_uri(), target_dir)
        assert (target_dir / ".git").is_dir()

    def test_clone_invalid_parameter(self, tmp_path: Path) -> None:
        with pytest.raises(
            RuntimeError, match=re.escape("Invalid Git parameter: --upload-pack")
        ):
            SystemGit.clone("--upload-pack=touch ./HELL", tmp_path)

    def test_checkout_1(self, temp_repo: TempRepoFixture) -> None:
        # case 1 - with 'target' arg
        SystemGit.checkout(temp_repo.init_commit[:12], temp_repo.path)
        assert get_head_sha(temp_repo.path) == temp_repo.init_commit

    def test_checkout_2(
        self, monkeypatch: pytest.MonkeyPatch, temp_repo: TempRepoFixture
    ) -> None:
        # case 2 - without 'target' arg
        monkeypatch.chdir(temp_repo.path)

        SystemGit.checkout(temp_repo.init_commit[:12])
        assert get_head_sha(temp_repo.path) == temp_repo.init_commit
