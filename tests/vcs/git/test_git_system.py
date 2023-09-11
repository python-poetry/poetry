from __future__ import annotations

import re
import shutil
import subprocess

from pathlib import Path

import pytest

from poetry.vcs.git.system import SystemGit


GIT_NOT_INSTALLLED = shutil.which("git") is None


def get_head_sha(cwd: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        text=True,
    ).strip()


@pytest.fixture(scope="module")
def current_repo_path() -> Path:
    return Path(__file__).parents[3]


@pytest.fixture(scope="module")
def current_sha(current_repo_path: Path) -> str:
    return get_head_sha(current_repo_path)


@pytest.fixture
def tmp_repo(current_repo_path: Path, tmp_path: Path, current_sha: str) -> Path:
    """Temporary repository + 1 redundant commit"""
    # create repo
    target_dir = tmp_path / "poetry-test"
    SystemGit.clone(current_repo_path.as_uri(), target_dir)

    # configure author
    subprocess.check_output(["git", "config", "user.name", "User"], cwd=target_dir)
    subprocess.check_output(
        ["git", "config", "user.email", "user@example.com"], cwd=target_dir
    )

    # add redundant commit
    stdout = subprocess.check_output(
        [
            "git",
            "commit",
            "--allow-empty",
            "--message=test commit",
            "--no-gpg-sign",  # avoid user interaction in case signing is turned on
        ],
        cwd=target_dir,
        text=True,
    )

    # ensure head commit changed
    assert re.match(r"^\[.+\] test commit", stdout)
    assert get_head_sha(target_dir) != current_sha

    return target_dir


@pytest.mark.skipif(GIT_NOT_INSTALLLED, reason="These tests requires git cli")
class TestSystemGit:
    def test_clone_success(self, current_repo_path: Path, tmp_path: Path) -> None:
        target_dir = tmp_path / "poetry-test"

        stdout = SystemGit.clone(current_repo_path.as_uri(), target_dir)

        assert re.search(r"Cloning into '.+[\\/]poetry-test'...", stdout)
        assert (target_dir / ".git").is_dir()

    def test_clone_invalid_parameter(self, tmp_path: Path) -> None:
        with pytest.raises(
            RuntimeError, match=re.escape("Invalid Git parameter: --upload-pack")
        ):
            SystemGit.clone("--upload-pack=touch ./HELL", tmp_path)

    def test_checkout_1(self, tmp_repo: Path, current_sha: str) -> None:
        # case 1 - with 'target' arg
        SystemGit.checkout(current_sha[:12], tmp_repo)
        assert get_head_sha(tmp_repo) == current_sha

    def test_checkout_2(
        self, monkeypatch: pytest.MonkeyPatch, tmp_repo: Path, current_sha: str
    ) -> None:
        # case 2 - without 'target' arg
        monkeypatch.chdir(tmp_repo)
        SystemGit.checkout(current_sha[:12])
        assert get_head_sha(tmp_repo) == current_sha
