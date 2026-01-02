from __future__ import annotations

import shutil

from typing import TYPE_CHECKING
from typing import cast

import pytest

from dulwich.client import FetchPackResult
from dulwich.repo import Repo

from poetry.console.exceptions import PoetryRuntimeError
from poetry.vcs.git.backend import Git
from poetry.vcs.git.backend import GitRefSpec
from poetry.vcs.git.backend import is_revision_sha
from poetry.vcs.git.backend import peeled_tag
from poetry.vcs.git.backend import urlpathjoin
from tests.helpers import MOCK_DEFAULT_GIT_REVISION


if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from tests.vcs.git.git_fixture import TempRepoFixture


VALID_SHA = "c5c7624ef64f34d9f50c3b7e8118f7f652fddbbd"

FULL_SHA_MAIN = "f7c3bc1d808e04732adf679965ccc34ca7ae3441"
FULL_SHA_TAG = "d4f6c2a8b9e1073451f28c96a5db7e3f9c2a8b7e"
SHORT_SHA = "f7c3bc1d"


@pytest.fixture()
def repo_mock(mocker: MockerFixture) -> Repo:
    repo = mocker.MagicMock(spec=Repo)

    repo.get_config.return_value.get.return_value = (
        b"https://github.com/python-poetry/poetry.git"
    )

    repo.head.return_value = MOCK_DEFAULT_GIT_REVISION.encode("utf-8")

    # Mock object store for short SHA resolution
    repo.object_store = mocker.MagicMock()
    repo.object_store.iter_prefix.return_value = [FULL_SHA_MAIN.encode()]

    return cast("Repo", repo)


@pytest.fixture()
def fetch_pack_result(mocker: MockerFixture) -> FetchPackResult:
    mock_fetch_pack_result = mocker.MagicMock(spec=FetchPackResult)
    mock_fetch_pack_result.refs = {
        b"refs/heads/main": FULL_SHA_MAIN.encode(),
        b"refs/heads/feature": b"a9b8c7d6e5f4321098765432109876543210abcd",
        b"refs/tags/v1.0.0": FULL_SHA_TAG.encode(),
        peeled_tag(b"refs/tags/v1.0.0"): FULL_SHA_TAG.encode(),
        b"HEAD": FULL_SHA_MAIN.encode(),
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
def test_peeled_tag(tag: str | bytes) -> None:
    tag = peeled_tag("my-tag")
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
        # Basic parameter tests
        (
            GitRefSpec(branch="main"),
            b"refs/heads/main",
            "main",
            None,
            None,
        ),
        (
            GitRefSpec(tag="v1.0.0"),
            peeled_tag(b"refs/tags/v1.0.0"),
            None,
            None,
            "v1.0.0",
        ),
        (
            GitRefSpec(branch="refs/heads/feature"),
            b"refs/heads/feature",
            "refs/heads/feature",
            None,
            None,
        ),
        # Cross-parameter resolution tests
        (
            GitRefSpec(revision="v1.0.0"),
            peeled_tag(b"refs/tags/v1.0.0"),
            None,
            None,
            "v1.0.0",
        ),
        (
            GitRefSpec(revision="main"),
            b"refs/heads/main",
            "main",
            None,
            None,
        ),
        (
            GitRefSpec(branch="v1.0.0"),
            peeled_tag(b"refs/tags/v1.0.0"),
            None,
            None,
            "v1.0.0",
        ),
        (
            GitRefSpec(revision="refs/heads/main"),
            b"refs/heads/main",
            "refs/heads/main",
            None,
            None,
        ),
        # SHA resolution tests with realistic values
        (
            GitRefSpec(revision=SHORT_SHA),
            b"refs/heads/main",
            None,
            FULL_SHA_MAIN,
            None,
        ),
        (
            GitRefSpec(revision=FULL_SHA_MAIN),
            b"refs/heads/main",
            None,
            FULL_SHA_MAIN,
            None,
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
        f"Failed to clone {source_url} at 'refs/heads/main',"
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
