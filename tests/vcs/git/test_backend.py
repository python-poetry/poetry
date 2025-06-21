from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import pytest

from dulwich.client import FetchPackResult
from dulwich.repo import Repo

from poetry.vcs.git.backend import Git
from poetry.vcs.git.backend import GitRefSpec
from poetry.vcs.git.backend import annotated_tag
from poetry.vcs.git.backend import is_revision_sha
from poetry.vcs.git.backend import urlpathjoin
from tests.helpers import MOCK_DEFAULT_GIT_REVISION


if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from tests.vcs.git.git_fixture import TempRepoFixture


VALID_SHA = "c5c7624ef64f34d9f50c3b7e8118f7f652fddbbd"


@pytest.fixture()
def repo_mock(mocker: MockerFixture) -> Repo:
    repo = mocker.MagicMock(spec=Repo)

    repo.get_config.return_value.get.return_value = (
        b"https://github.com/python-poetry/poetry.git"
    )

    repo.head.return_value = MOCK_DEFAULT_GIT_REVISION.encode("utf-8")

    # Mock object store for short SHA resolution
    repo.object_store = mocker.MagicMock()
    repo.object_store.iter_prefix.return_value = [b"abc123def456789abcdef"]

    # Note: cache clearing removed to avoid import conflicts

    return cast("Repo", repo)


@pytest.fixture()
def fetch_pack_result(mocker: MockerFixture) -> FetchPackResult:
    mock_fetch_pack_result = mocker.MagicMock(spec=FetchPackResult)
    mock_fetch_pack_result.refs = {
        b"refs/heads/main": b"abc123def456789abcdef",
        b"refs/tags/v1.0.0": b"def456abc123789abcdef",
        annotated_tag(b"refs/tags/v1.0.0"): b"def456abc123789abcdef",
        b"HEAD": b"abc123def456789abcdef",
    }
    mock_fetch_pack_result.symrefs = {b"HEAD": b"refs/heads/main"}

    return cast("FetchPackResult", mock_fetch_pack_result)


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


def test_get_remote_url(repo_mock: Repo) -> None:
    assert (
        Git.get_remote_url(repo_mock) == "https://github.com/python-poetry/poetry.git"
    )


def test_get_revision(repo_mock: Repo) -> None:
    assert Git.get_revision(repo_mock) == MOCK_DEFAULT_GIT_REVISION


def test_info(repo_mock: Repo) -> None:
    info = Git.info(repo_mock)

    assert info.origin == "https://github.com/python-poetry/poetry.git"
    assert (
        info.revision == MOCK_DEFAULT_GIT_REVISION
    )  # revision already mocked in helper


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


def test_git_refspec() -> None:
    git_ref = GitRefSpec("main", "1234", "v2")

    assert git_ref.branch == "main"
    assert git_ref.revision == "1234"
    assert git_ref.tag == "v2"
    assert git_ref.ref == b"HEAD"


@pytest.mark.parametrize(
    "refspec, expected_ref, expected_branch, expected_revision, expected_tag",
    [
        (
            GitRefSpec(branch="main"),
            b"refs/heads/main",
            "main",
            None,
            None,
        ),
        (
            GitRefSpec(revision="v1.0.0"),
            annotated_tag(b"refs/tags/v1.0.0"),
            None,
            None,
            "v1.0.0",
        ),
        (
            GitRefSpec(revision="abc123"),
            b"refs/heads/main",
            None,
            "abc123def456789abcdef",
            None,
        ),
        (
            GitRefSpec(revision="abc123def456789abcdef"),
            b"refs/heads/main",
            None,
            "abc123def456789abcdef",
            None,
        ),
        (
            GitRefSpec(branch="v1.0.0"),
            annotated_tag(b"refs/tags/v1.0.0"),
            None,
            None,
            "v1.0.0",
        ),
    ],
)
def test_git_ref_spec_resolve(
    fetch_pack_result: FetchPackResult,
    repo_mock: Repo,
    refspec: GitRefSpec,
    expected_ref: bytes,
    expected_branch: str | None,
    expected_revision: str | None,
    expected_tag: str | None,
) -> None:
    refspec.resolve(fetch_pack_result, repo_mock)

    assert refspec.ref == expected_ref
    assert refspec.branch == expected_branch
    assert refspec.revision == expected_revision
    assert refspec.tag == expected_tag


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
